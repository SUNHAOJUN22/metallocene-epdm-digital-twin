"""Chemical-engineering sanity checks for simulation results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from .units import assert_conversion_range, assert_heat_duty_sign, assert_weight_percent_sum
from .utils import safe_divide


SEVERITY_RANK = {"info": 0, "warning": 1, "error": 2}


@dataclass(frozen=True)
class EngineeringCheckResult:
    """One engineering logic check result."""

    passed: bool
    severity: str
    message: str
    affected_module: str
    suggested_fix: str

    def as_dict(self) -> dict[str, Any]:
        """Return a table row."""
        return {
            "passed": self.passed,
            "severity": self.severity,
            "affected_module": self.affected_module,
            "message": self.message,
            "suggested_fix": self.suggested_fix,
        }


def _check(condition: bool, severity: str, module: str, message: str, suggested_fix: str) -> EngineeringCheckResult:
    """Build a normalized check result."""
    return EngineeringCheckResult(bool(condition), "info" if condition else severity, message, module, suggested_fix)


def run_engineering_checks(result: Any) -> list[EngineeringCheckResult]:
    """Run mass, reactor, energy, transport and flash sanity checks."""
    checks: list[EngineeringCheckResult] = []
    kpis = getattr(result, "kpis", {})
    reactor = getattr(result, "reactor", None)
    streams = getattr(result, "streams", {})

    closure = abs(float(kpis.get("mass_balance_error_pct", 0.0)))
    checks.append(
        _check(
            closure <= 1.0,
            "warning",
            "flowsheet",
            f"总物料衡算闭合误差 {closure:.3g}%",
            "检查闪蒸K值、回收循环和产品/气相流量。",
        )
    )

    if reactor is not None:
        for monomer, conversion in reactor.conversions.items():
            try:
                assert_conversion_range(conversion, as_percent=True, name=f"{monomer} conversion")
                valid = True
            except ValueError:
                valid = False
            checks.append(
                _check(valid, "error", "reactor", f"{monomer} 转化率 {conversion:.3g}% 位于 0-100%。", "限制反应速率和单体消耗量。")
            )
        monomer_mass = 0.0
        for monomer, mol in reactor.consumed_mol_h.items():
            mw = {"ethylene": 28.054, "propylene": 42.081, "ENB": 120.19}.get(monomer, 0.0)
            monomer_mass += max(float(mol), 0.0) * mw / 1000.0
        polymer_mass = max(float(reactor.polymer_kg_h), 0.0)
        polymer_error = abs(safe_divide(polymer_mass - monomer_mass, max(monomer_mass, 1.0e-12), 0.0))
        checks.append(
            _check(
                polymer_error <= 1.0e-6,
                "error",
                "reactor",
                f"聚合物质量与单体消耗质量相对误差 {polymer_error:.3g}",
                "检查单体MW、consumed_mol_h和segment mass计算。",
            )
        )
        comp = dict(reactor.polymer_composition_wt)
        try:
            assert_weight_percent_sum(comp, tolerance=1.0e-4)
            comp_ok = True
        except ValueError:
            comp_ok = False
        checks.append(
            _check(comp_ok, "error", "product", f"产品组成总和 {sum(comp.values()):.4g} wt%", "归一化C2/C3/ENB产品组成。")
        )
        checks.append(
            _check(
                float(getattr(reactor, "Cstar_mol_L", 0.0)) >= 0.0,
                "error",
                "reactor",
                f"活性中心浓度 Cstar={float(getattr(reactor, 'Cstar_mol_L', 0.0)):.3g} mol/L",
                "催化剂活性中心不得为负。",
            )
        )

    q_rxn = float(kpis.get("heat_duty_kJ_h", 0.0))
    try:
        assert_heat_duty_sign(q_rxn, exothermic=True, name="Q_rxn_kJ_h")
        heat_positive = True
    except ValueError:
        heat_positive = False
    checks.append(_check(heat_positive, "error", "heat_balance", f"放热聚合移热需求 Q={q_rxn:.3g} kJ/h", "检查反应热符号约定。"))
    checks.append(
        _check(
            float(kpis.get("deltaT_ad_K", 0.0)) <= 20.0 or str(kpis.get("thermal_risk", "")).lower() == "high",
            "warning",
            "safety",
            f"绝热温升 {float(kpis.get('deltaT_ad_K', 0.0)):.3g} K，热风险 {kpis.get('thermal_risk')}",
            "高绝热温升时必须标为 high 或加强冷却。",
        )
    )
    checks.append(
        _check(
            float(kpis.get("cooling_margin_kW", 0.0)) >= 0.0 or "不足" in str(kpis.get("heat_transfer_status", "")),
            "error",
            "heat_balance",
            f"移热裕度 {float(kpis.get('cooling_margin_kW', 0.0)):.3g} kW，状态 {kpis.get('heat_transfer_status')}",
            "cooling_margin < 0 时必须报警。",
        )
    )

    for field, unit in [
        ("liquid_density_kg_m3", "kg/m3"),
        ("Cp_liq_kJ_kgK", "kJ/kg/K"),
        ("dynamic_viscosity_Pa_s", "Pa.s"),
        ("thermal_conductivity_W_mK", "W/m/K"),
    ]:
        value = float(kpis.get(field, 0.0))
        checks.append(_check(value > 0.0, "error", "fluid_props", f"{field}={value:.3g} {unit}", "物性必须为正。"))

    checks.append(
        _check(
            float(kpis.get("pipe_pressure_drop_kPa", 0.0)) >= 0.0 and float(kpis.get("pump_power_kW", 0.0)) >= 0.0,
            "error",
            "hydraulics",
            f"压降 {float(kpis.get('pipe_pressure_drop_kPa', 0.0)):.3g} kPa，泵功 {float(kpis.get('pump_power_kW', 0.0)):.3g} kW",
            "检查Darcy-Weisbach压降和流量输入。",
        )
    )

    for name in ("Flash-1 vapor", "Flash-2 vapor"):
        stream = streams.get(name)
        if stream is not None:
            checks.append(
                _check(
                    float(getattr(stream, "polymer_mass_kg_h", 0.0)) <= 1.0e-9,
                    "error",
                    "flash",
                    f"{name} polymer mass {float(getattr(stream, 'polymer_mass_kg_h', 0.0)):.3g} kg/h",
                    "聚合物伪组分必须保留在液相。",
                )
            )

    vapor_fraction_ok = 0.0 <= float(kpis.get("flash1_vapor_fraction", 0.0)) <= 1.0 and 0.0 <= float(kpis.get("flash2_vapor_fraction", 0.0)) <= 1.0
    checks.append(_check(vapor_fraction_ok, "error", "flash", "闪蒸汽化率位于0-1。", "约束Rachford-Rice vapor fraction。"))
    return checks


def checks_dataframe(checks: list[EngineeringCheckResult]) -> pd.DataFrame:
    """Return engineering checks as a DataFrame."""
    return pd.DataFrame([check.as_dict() for check in checks])


def overall_engineering_status(checks: list[EngineeringCheckResult]) -> str:
    """Return green/yellow/red status for a list of checks."""
    failed = [check for check in checks if not check.passed]
    if not failed:
        return "green"
    worst = max(SEVERITY_RANK.get(check.severity, 0) for check in failed)
    return "red" if worst >= SEVERITY_RANK["error"] else "yellow"
