"""Conservation and closure checks for process simulation results.

The functions in this module intentionally operate on the existing result
objects through duck typing.  That keeps the checks reusable for steady
flowsheet results, dynamic endpoint summaries, and future polymerization
templates without coupling them to one default case.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from .components import load_components
from .reaction_templates import segment_map_from_template
from .streams import Stream
from .utils import TINY, positive, safe_divide


@dataclass(frozen=True)
class ConservationResult:
    """One numerical conservation check."""

    balance_type: str
    reference: float
    calculated: float
    absolute_error: float
    relative_error_pct: float
    tolerance: float
    passed: bool
    severity: str
    message: str
    suggested_fix: str = ""

    def as_dict(self) -> dict[str, Any]:
        """Return a report/UI friendly dictionary."""
        return {
            "balance_type": self.balance_type,
            "reference": self.reference,
            "calculated": self.calculated,
            "absolute_error": self.absolute_error,
            "relative_error_pct": self.relative_error_pct,
            "tolerance": self.tolerance,
            "passed": self.passed,
            "severity": self.severity,
            "message": self.message,
            "suggested_fix": self.suggested_fix,
        }


@dataclass(frozen=True)
class ConservationDiagnostic:
    """Likely source and fix for a failed conservation check."""

    failed_balance: str
    likely_source: str
    suspected_unit_issue: str
    suspected_stream: str
    suggested_fix: str
    severity: str

    def as_dict(self) -> dict[str, Any]:
        """Return a report/UI friendly row."""
        return self.__dict__.copy()


def _result(
    balance_type: str,
    reference: float,
    calculated: float,
    tolerance: float,
    message: str,
    suggested_fix: str = "",
) -> ConservationResult:
    """Build a finite conservation result with relative error."""
    ref = float(reference or 0.0)
    calc = float(calculated or 0.0)
    abs_error = abs(calc - ref)
    rel_error = 100.0 * safe_divide(abs_error, max(abs(ref), TINY), 0.0)
    passed = rel_error <= tolerance
    severity = "ok" if passed else ("warning" if rel_error <= 3.0 * tolerance else "error")
    return ConservationResult(
        balance_type=balance_type,
        reference=ref,
        calculated=calc,
        absolute_error=abs_error,
        relative_error_pct=rel_error,
        tolerance=tolerance,
        passed=passed,
        severity=severity,
        message=message if passed else f"{message}，闭合偏差 {rel_error:.3g}%。",
        suggested_fix=suggested_fix,
    )


def conservation_dataframe(results: list[ConservationResult]) -> pd.DataFrame:
    """Convert conservation results to a DataFrame."""
    return pd.DataFrame([item.as_dict() for item in results])


def conservation_diagnostics_dataframe(diagnostics: list[ConservationDiagnostic]) -> pd.DataFrame:
    """Convert conservation diagnostics to a DataFrame."""
    return pd.DataFrame([item.as_dict() for item in diagnostics])


def stream_mass(stream: Stream | None) -> float:
    """Return stream total mass flow in kg/h, handling missing streams."""
    if stream is None:
        return 0.0
    return positive(stream.total_mass_flow())


def total_mass_balance(result: Any, tolerance_pct: float = 1.0) -> ConservationResult:
    """Check overall process mass closure across feed, product and purge/recycle outputs."""
    streams = getattr(result, "streams", {}) or {}
    feed = stream_mass(streams.get("Feed"))
    product = stream_mass(streams.get("Polymer product"))
    flash_vapor = stream_mass(streams.get("Flash-1 vapor")) + stream_mass(streams.get("Flash-2 vapor"))
    calculated = product + flash_vapor
    return _result(
        "total_mass_balance",
        feed,
        calculated,
        tolerance_pct,
        "总物料衡算闭合",
        "检查闪蒸分配、回收/放空气和负流量保护。",
    )


def component_mass_balance(result: Any, component: str, tolerance_pct: float = 1.0) -> ConservationResult:
    """Check a component or segment mass closure across the steady flowsheet."""
    streams = getattr(result, "streams", {}) or {}
    reactor = getattr(result, "reactor", None)
    feed = positive(streams.get("Feed").component_mass(component) if streams.get("Feed") else 0.0)
    product_stream = streams.get("Polymer product")
    molecular_out = positive(product_stream.component_mass(component) if product_stream else 0.0)
    molecular_out += positive(streams.get("Flash-1 vapor").component_mass(component) if streams.get("Flash-1 vapor") else 0.0)
    molecular_out += positive(streams.get("Flash-2 vapor").component_mass(component) if streams.get("Flash-2 vapor") else 0.0)
    segment_map = {"ethylene": "E", "propylene": "P", "ENB": "D"}
    segment_mass = 0.0
    if component in segment_map and reactor is not None:
        segment_mass = positive(getattr(reactor.outlet, "segment_masses_kg_h", {}).get(segment_map[component], 0.0))
    calculated = molecular_out + segment_mass
    return _result(
        f"component_mass_balance:{component}",
        feed,
        calculated,
        tolerance_pct,
        f"{component} 组分/聚合段质量闭合",
        "检查该组分的反应消耗、闪蒸分配和聚合段映射。",
    )


def reactor_monomer_polymer_balance(reactor_result: Any, tolerance_pct: float = 0.5) -> ConservationResult:
    """Check consumed monomer mass against polymer production."""
    components = load_components()
    consumed = getattr(reactor_result, "consumed_mol_h", {}) or {}
    consumed_mass = sum(
        positive(mol) * components[name].MW / 1000.0
        for name, mol in consumed.items()
        if name in components
    )
    polymer = positive(getattr(reactor_result, "polymer_kg_h", 0.0))
    return _result(
        "reactor_monomer_polymer_balance",
        consumed_mass,
        polymer,
        tolerance_pct,
        "反应器单体消耗质量与聚合物生成质量闭合",
        "检查单体分子量、消耗量和聚合段质量计算。",
    )


def segment_balance(reactor_result: Any, tolerance_pct: float = 0.5, reaction_template_id: str = "EPDM_EPM_metallocene_solution") -> ConservationResult:
    """Check E/P/D segment mass sum against polymer production."""
    outlet = getattr(reactor_result, "outlet", None)
    segment_names = set(segment_map_from_template(reaction_template_id).values())
    segments = getattr(outlet, "segment_masses_kg_h", {})
    segment_mass = sum(positive(v) for key, v in segments.items() if key in segment_names)
    polymer = positive(getattr(reactor_result, "polymer_kg_h", 0.0))
    return _result(
        "segment_balance",
        polymer,
        segment_mass,
        tolerance_pct,
        "E/P/D聚合段质量之和与聚合物质量闭合",
        "检查聚合段映射和产品组成归一化。",
    )


def flash_mass_balance(inlet: Stream, vapor: Stream, liquid: Stream, tolerance_pct: float = 0.5) -> ConservationResult:
    """Check flash inlet mass equals vapor plus liquid outlet mass."""
    return _result(
        f"flash_mass_balance:{getattr(inlet, 'name', 'flash')}",
        stream_mass(inlet),
        stream_mass(vapor) + stream_mass(liquid),
        tolerance_pct,
        "闪蒸单元质量闭合",
        "检查Rachford-Rice气液分配和聚合物留液假设。",
    )


def energy_release_balance(reactor_result: Any, heat_balance: Any, tolerance_pct: float = 0.5) -> ConservationResult:
    """Check reaction heat equals consumed moles times heat of polymerization."""
    delta_h = getattr(heat_balance, "deltaH_polymerization", {}) or {}
    consumed = getattr(reactor_result, "consumed_mol_h", {}) or {}
    reference = sum(positive(consumed.get(name, 0.0)) * abs(float(delta_h.get(name, 0.0))) for name in consumed)
    calculated = positive(getattr(heat_balance, "Q_rxn_kJ_h", 0.0))
    return _result(
        "energy_release_balance",
        reference,
        calculated,
        tolerance_pct,
        "聚合放热与单体消耗量闭合",
        "检查deltaH默认值、符号约定和反应器消耗量。",
    )


def product_composition_balance(kpis: dict[str, Any], tolerance_pct: float = 0.5) -> ConservationResult:
    """Check product C2/C3/ENB wt% sums to 100."""
    calculated = positive(kpis.get("C2_wt", 0.0)) + positive(kpis.get("C3_wt", 0.0)) + positive(kpis.get("ENB_wt", 0.0))
    return _result(
        "product_composition_balance",
        100.0,
        calculated,
        tolerance_pct,
        "产品C2/C3/ENB组成闭合",
        "检查产品组成归一化和微量组分处理。",
    )


def recycle_balance(recycle_result: Any, tolerance_pct: float = 1.0) -> ConservationResult:
    """Check recycle solver closure error is finite and within tolerance."""
    closure = abs(float(getattr(recycle_result, "closure_error", 0.0) or 0.0))
    tolerance_abs = max(tolerance_pct, 1.0e-6)
    passed = closure <= tolerance_abs
    return ConservationResult(
        balance_type="recycle_balance",
        reference=0.0,
        calculated=closure,
        absolute_error=closure,
        relative_error_pct=0.0 if passed else 100.0,
        tolerance=tolerance_abs,
        passed=passed,
        severity="ok" if passed else "warning",
        message="回收循环闭合误差" if passed else f"回收循环闭合误差 {closure:.3g} kg/h。",
        suggested_fix="" if passed else "检查purge比例、tear stream迭代和补充进料。",
    )


def run_conservation_checks(result: Any) -> list[ConservationResult]:
    """Run the default conservation suite for a flowsheet result."""
    checks = [
        total_mass_balance(result),
        product_composition_balance(getattr(result, "kpis", {}) or {}),
        reactor_monomer_polymer_balance(getattr(result, "reactor", None)),
        segment_balance(getattr(result, "reactor", None)),
        energy_release_balance(getattr(result, "reactor", None), getattr(result, "heat_balance", None)),
    ]
    for component in ("ethylene", "propylene", "ENB", "hydrogen", getattr(getattr(result, "config", None), "solvent", "hexane")):
        checks.append(component_mass_balance(result, component))
    streams = getattr(result, "streams", {}) or {}
    if {"Quenched solution", "Flash-1 vapor", "Flash-1 liquid"}.issubset(streams):
        checks.append(flash_mass_balance(streams["Quenched solution"], streams["Flash-1 vapor"], streams["Flash-1 liquid"]))
    if {"Flash-1 liquid", "Flash-2 vapor", "Polymer product"}.issubset(streams):
        checks.append(flash_mass_balance(streams["Flash-1 liquid"], streams["Flash-2 vapor"], streams["Polymer product"]))
    if getattr(result, "recycle_solver", None) is not None:
        checks.append(recycle_balance(result.recycle_solver))
    return checks


def diagnose_conservation_results(results: list[ConservationResult]) -> list[ConservationDiagnostic]:
    """Map failed conservation checks to likely model/stream sources."""
    diagnostics: list[ConservationDiagnostic] = []
    for item in results:
        if item.passed:
            continue
        likely_source = "flowsheet"
        suspected_unit = "unit conversion or split fraction"
        suspected_stream = ""
        fix = item.suggested_fix or "检查输入单位、流量符号和模型适用范围。"
        if item.balance_type.startswith("flash_mass_balance"):
            likely_source = "flash"
            suspected_stream = item.balance_type.split(":", 1)[-1]
            suspected_unit = "kg/h vs mol/h split or polymer carryover"
            fix = "检查flash inlet/vapor/liquid stream质量和polymer留液逻辑。"
        elif item.balance_type.startswith("component_mass_balance"):
            component = item.balance_type.split(":", 1)[-1]
            likely_source = "reactor/flash/product_properties"
            suspected_stream = component
            suspected_unit = "component kg/h vs incorporated segment mass"
            fix = f"检查 {component} 的进料、未反应量、闪蒸气相和聚合段映射。"
        elif item.balance_type == "energy_release_balance":
            likely_source = "heat_balance"
            suspected_stream = "reactor consumed_mol_h"
            suspected_unit = "deltaH sign, mol/h vs kmol/h, kJ/h vs kW"
            fix = "检查deltaH是否为负值输入，Q_rxn是否为正移热需求，并确认consumed_mol_h单位。"
        elif item.balance_type == "product_composition_balance":
            likely_source = "product_properties"
            suspected_stream = "polymer composition"
            suspected_unit = "wt% normalization"
            fix = "检查C2/C3/ENB质量分数是否按聚合物段质量归一化。"
        elif item.balance_type == "recycle_balance":
            likely_source = "recycle_solver"
            suspected_stream = "tear stream"
            suspected_unit = "kg/h closure"
            fix = "检查purge_fraction、fresh makeup和tear迭代容差。"
        elif item.balance_type == "total_mass_balance":
            likely_source = "flowsheet/recycle/purge"
            suspected_stream = "Feed/Product/Flash vapor"
            suspected_unit = "kg/h total mass"
            fix = "对比Feed、Product、Flash-1 vapor、Flash-2 vapor和purge质量流。"
        diagnostics.append(
            ConservationDiagnostic(
                failed_balance=item.balance_type,
                likely_source=likely_source,
                suspected_unit_issue=suspected_unit,
                suspected_stream=suspected_stream,
                suggested_fix=fix,
                severity=item.severity,
            )
        )
    return diagnostics
