"""Template-aware process flowsheet adapter.

This module introduces the V4.7 template flowsheet contract while keeping the
validated EPDM flowsheet as the application adapter.  Generic templates use a
lightweight apparent polymerization path with explicit mass/segment closure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from .feed_adapter import build_template_feed_stream, validate_template_feed_map
from .flowsheet import FlowsheetResult, ProcessConfig, _run_epdm_flowsheet_impl
from .kinetics import KineticParameters, calculate_template_conversions, calculate_template_polymer_segments
from .kpi_adapter import build_template_kpis
from .kpi_schema import KPI, kpis_to_dataframe
from .reaction_templates import template_with_fallback
from .streams import Stream
from .template_config import TemplateProcessConfig, template_config_to_process_config
from .utils import clamp, model_dump_compat, positive, safe_divide


@dataclass
class TemplateFlowsheetResult:
    """Template-aware flowsheet result."""

    template_config: TemplateProcessConfig
    template_id: str
    streams: dict[str, Stream]
    unit_results: dict[str, dict[str, Any]]
    reactor_result: Any
    flash_results: dict[str, Any]
    heat_balance: Any
    fluid_properties: Any
    pipe_hydraulics: Any
    recycle_result: Any
    template_kpis: list[KPI]
    application_kpis: dict[str, Any]
    warnings: list[str] = field(default_factory=list)
    legacy_flowsheet: FlowsheetResult | None = None

    def stream_table(self) -> pd.DataFrame:
        return template_stream_table(self)

    def unit_table(self) -> pd.DataFrame:
        return template_unit_table(self)

    def kpi_table(self) -> pd.DataFrame:
        return kpis_to_dataframe(self.template_kpis)


def _is_epdm_template(template_id: str) -> bool:
    return template_id == "EPDM_EPM_metallocene_solution"


def run_epdm_flowsheet_adapter(process_config: ProcessConfig | dict[str, Any] | TemplateProcessConfig | None = None) -> TemplateFlowsheetResult:
    """Run the established EPDM flowsheet and wrap it in the template contract."""
    cfg = template_config_to_process_config(process_config) if isinstance(process_config, TemplateProcessConfig) else process_config
    result = _run_epdm_flowsheet_impl(cfg)
    template_cfg = TemplateProcessConfig.from_process_config(result.config, "EPDM_EPM_metallocene_solution")
    return TemplateFlowsheetResult(
        template_config=template_cfg,
        template_id=template_cfg.template_id,
        streams=result.streams,
        unit_results=result.unit_results,
        reactor_result=result.reactor,
        flash_results={"flash1": result.flash1, "flash2": result.flash2},
        heat_balance=result.heat_balance,
        fluid_properties=result.fluid_properties,
        pipe_hydraulics=result.pipe_hydraulics,
        recycle_result=result.recycle_solver,
        template_kpis=build_template_kpis(template_cfg.template_id, result),
        application_kpis=dict(result.kpis),
        warnings=list(result.warnings),
        legacy_flowsheet=result,
    )


def run_template_flowsheet(template_config: TemplateProcessConfig | dict[str, Any]) -> TemplateFlowsheetResult:
    """Run a template-aware flowsheet.

    The EPDM template delegates to the validated legacy flowsheet.  Generic
    templates use an apparent conversion model, suitable for interface tests
    and future calibrated kernels, while preserving mass and segment balances.
    """
    cfg = template_config if isinstance(template_config, TemplateProcessConfig) else TemplateProcessConfig(**template_config)
    if _is_epdm_template(cfg.template_id):
        return run_epdm_flowsheet_adapter(cfg)
    template, template_warnings = template_with_fallback(cfg.template_id)
    warnings = list(template_warnings)
    feed_checks = validate_template_feed_map(cfg)
    warnings.extend(check.message for check in feed_checks if not check.passed and check.severity != "error")
    errors = [check for check in feed_checks if not check.passed and check.severity == "error"]
    if errors:
        warnings.extend(check.message for check in errors)
    feed = build_template_feed_stream(cfg)
    params = KineticParameters()
    conversion_factor = clamp(cfg.residence_time_min / (cfg.residence_time_min + 35.0), 0.0, 0.85)
    catalyst_factor = clamp(cfg.catalyst_umol_h / (cfg.catalyst_umol_h + 80.0), 0.0, 1.0)
    pressure_penalty = 1.0 / (1.0 + 0.08 * max(cfg.pressure_MPa - 1.0, 0.0))
    consumed_moles = {}
    feed_moles = {}
    for monomer in template.monomers:
        feed_moles[monomer] = positive(feed.molar_flows.get(monomer, 0.0))
        consumed_moles[monomer] = min(feed_moles[monomer], feed_moles[monomer] * conversion_factor * catalyst_factor * pressure_penalty)
    segment_masses = calculate_template_polymer_segments(template.template_id, consumed_moles)
    conversions = calculate_template_conversions(template.template_id, feed_moles, consumed_moles)
    reactor_out = feed.copy_stream("Template reactor outlet")
    for monomer, consumed in consumed_moles.items():
        reactor_out.molar_flows[monomer] = max(reactor_out.molar_flows.get(monomer, 0.0) - consumed, 0.0)
        reactor_out.mass_flows[monomer] = reactor_out.molar_flows[monomer] * template.molecular_weights.get(monomer, 100.0) / 1000.0
    reactor_out.update_solids()
    reactor_out.add_polymer(segment_masses)
    total_segment = sum(segment_masses.values())
    composition = {
        segment: 100.0 * safe_divide(mass, total_segment, 0.0) for segment, mass in segment_masses.items()
    }
    q_rxn_kJ_h = sum(consumed_moles[m] * abs(template.heat_of_polymerization.get(m, -80.0)) for m in template.monomers)
    flash_vapor = reactor_out.copy_stream("Template flash vapor")
    flash_liquid = reactor_out.copy_stream("Template flash liquid")
    vapor_split = 0.0
    for comp in list(flash_vapor.mass_flows):
        split = 0.0
        if comp in {"hydrogen", "ethylene", "propylene"} or comp.startswith("monomer_"):
            split = clamp(0.15 + 0.25 * max(1.0 - cfg.flash1_P_MPa, 0.0), 0.0, 0.75)
        elif comp == cfg.solvent:
            split = clamp(0.03 + 0.15 * max(1.0 - cfg.flash2_P_MPa, 0.0), 0.0, 0.45)
        flash_vapor.mass_flows[comp] *= split
        flash_liquid.mass_flows[comp] *= 1.0 - split
        vapor_split += split
    flash_vapor.polymer_mass_kg_h = 0.0
    flash_vapor.segment_masses_kg_h = {}
    flash_liquid.polymer_mass_kg_h = reactor_out.polymer_mass_kg_h
    flash_liquid.segment_masses_kg_h = dict(reactor_out.segment_masses_kg_h)
    for stream in [flash_vapor, flash_liquid]:
        for monomer in template.monomers:
            stream.molar_flows[monomer] = stream.mass_flows.get(monomer, 0.0) * 1000.0 / max(template.molecular_weights.get(monomer, 100.0), 1.0e-12)
        stream.update_solids()
    product = flash_liquid.copy_stream("Template polymer product")
    product.phase = "polymer solution"
    product.update_solids()
    kpis = {
        "template_id": template.template_id,
        "polymer_kg_h": product.polymer_mass_kg_h,
        "segment_composition_wt": composition,
        "monomer_conversions": {m: 100.0 * conversions[m] for m in template.monomers},
        "heat_duty_kJ_h": q_rxn_kJ_h,
        "heat_duty_kW": q_rxn_kJ_h / 3600.0,
        "solids_wt": product.solids_wt,
        "flash_vapor_fraction": safe_divide(flash_vapor.total_mass_flow(), reactor_out.total_mass_flow(), 0.0),
        "mass_balance_error_pct": template_mass_balance_from_streams(feed, product, flash_vapor),
    }
    template_kpis = _generic_template_kpis(template.template_id, kpis, composition)
    streams = {
        "Template feed": feed,
        "Template reactor outlet": reactor_out,
        "Template flash vapor": flash_vapor,
        "Template polymer product": product,
    }
    unit_results = {
        "Template reactor": {
            "polymer_kg_h": product.polymer_mass_kg_h,
            "heat_duty_kJ_h": q_rxn_kJ_h,
            "conversions": str(kpis["monomer_conversions"]),
        },
        "Template flash": {"vapor_fraction": kpis["flash_vapor_fraction"]},
    }
    return TemplateFlowsheetResult(
        template_config=cfg,
        template_id=template.template_id,
        streams=streams,
        unit_results=unit_results,
        reactor_result={"feed_moles": feed_moles, "consumed_moles": consumed_moles, "segment_masses_kg_h": segment_masses},
        flash_results={"flash_vapor": flash_vapor, "flash_liquid": product},
        heat_balance={"Q_rxn_kJ_h": q_rxn_kJ_h, "Q_rxn_kW": q_rxn_kJ_h / 3600.0},
        fluid_properties=None,
        pipe_hydraulics=None,
        recycle_result=None,
        template_kpis=template_kpis,
        application_kpis=kpis,
        warnings=warnings,
    )


def _generic_template_kpis(template_id: str, kpis: dict[str, Any], composition: dict[str, float]) -> list[KPI]:
    rows = [
        KPI("polymer_production", float(kpis["polymer_kg_h"]), "kg/h", "production", template_id, "polymer", "polymer_kg_h", (0.0, None)),
        KPI("heat_duty", float(kpis["heat_duty_kW"]), "kW", "energy", template_id, "reaction", "heat_duty_kW", (0.0, None)),
        KPI("solids", float(kpis["solids_wt"]), "wt%", "fluid", template_id, "polymer", "solids_wt", (0.0, 100.0)),
    ]
    for segment, value in composition.items():
        rows.append(KPI(f"{segment}_segment_wt", float(value), "wt%", "composition", template_id, segment, "", (0.0, 100.0)))
    for monomer, value in kpis.get("monomer_conversions", {}).items():
        rows.append(KPI(f"{monomer}_conversion", float(value), "%", "conversion", template_id, monomer, "", (0.0, 100.0)))
    return rows


def template_stream_table(result: TemplateFlowsheetResult | FlowsheetResult) -> pd.DataFrame:
    """Return a stream table for either template or legacy flowsheet results."""
    if isinstance(result, FlowsheetResult):
        return result.stream_table()
    rows = []
    for name, stream in result.streams.items():
        row = {
            "stream": name,
            "template_id": result.template_id,
            "T_C": stream.temperature_K - 273.15,
            "P_MPa": stream.pressure_Pa / 1.0e6,
            "phase": stream.phase,
            "total_kg_h": stream.total_mass_flow(),
            "polymer_kg_h": stream.polymer_mass_kg_h,
            "solids_wt": stream.solids_wt,
        }
        for comp, value in stream.mass_flows.items():
            row[f"{comp}_kg_h"] = value
        rows.append(row)
    return pd.DataFrame(rows)


def template_unit_table(result: TemplateFlowsheetResult | FlowsheetResult) -> pd.DataFrame:
    """Return a unit-operation table for either template or legacy flowsheet results."""
    if isinstance(result, FlowsheetResult):
        return result.unit_table()
    rows = []
    for unit, values in result.unit_results.items():
        row = {"unit": unit, "template_id": result.template_id}
        row.update(values)
        rows.append(row)
    return pd.DataFrame(rows)


def template_mass_balance_from_streams(feed: Stream, product: Stream, vapor: Stream) -> float:
    """Return mass-balance closure error percent for a simplified template split."""
    inlet = feed.total_mass_flow()
    outlet = product.total_mass_flow() + vapor.total_mass_flow()
    return 100.0 * safe_divide(outlet - inlet, max(inlet, 1.0e-12), 0.0)


def template_mass_balance(result: TemplateFlowsheetResult | FlowsheetResult) -> dict[str, float]:
    """Return template-aware mass-balance summary."""
    if isinstance(result, FlowsheetResult):
        feed = result.streams["Feed"].total_mass_flow()
        outlet = result.streams["Polymer product"].total_mass_flow() + result.streams["Flash-1 vapor"].total_mass_flow() + result.streams["Flash-2 vapor"].total_mass_flow()
    else:
        first = next(iter(result.streams.values()))
        feed = first.total_mass_flow()
        product = result.streams.get("Template polymer product")
        vapor = result.streams.get("Template flash vapor")
        outlet = (product.total_mass_flow() if product is not None else 0.0) + (vapor.total_mass_flow() if vapor is not None else 0.0)
    return {
        "feed_kg_h": feed,
        "outlet_kg_h": outlet,
        "closure_error_pct": 100.0 * safe_divide(outlet - feed, max(feed, 1.0e-12), 0.0),
    }


def template_flowsheet_dataframe(result: TemplateFlowsheetResult) -> pd.DataFrame:
    """Return a compact report dataframe for the template flowsheet."""
    payload = model_dump_compat(result.template_config)
    return pd.DataFrame(
        [
            {"section": "config", "name": key, "value": str(value)}
            for key, value in payload.items()
        ]
        + [
            {"section": "mass_balance", "name": key, "value": value}
            for key, value in template_mass_balance(result).items()
        ]
    )
