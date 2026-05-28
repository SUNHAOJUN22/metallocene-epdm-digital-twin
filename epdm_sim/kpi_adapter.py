"""Adapters from legacy flowsheet KPIs to template-aware KPI rows."""

from __future__ import annotations

from typing import Any

from .kpi_schema import KPI, validate_kpi_bounds, kpis_to_dataframe
from .reaction_templates import template_with_fallback
from .utils import positive


def build_template_kpis(template_id: str, flowsheet_result: Any) -> list[KPI]:
    """Build template-aware KPI rows while preserving EPDM compatibility aliases."""
    template, warnings = template_with_fallback(template_id)
    kpis = getattr(flowsheet_result, "kpis", {}) or {}
    reactor = getattr(flowsheet_result, "reactor", None)
    rows: list[KPI] = []
    for monomer in template.monomers:
        segment = template.polymer_segments.get(monomer, monomer)
        comp_key = {"ethylene": "C2_wt", "propylene": "C3_wt", "ENB": "ENB_wt"}.get(monomer, f"{segment}_wt")
        conv_key = {"ethylene": "C2_conversion_pct", "propylene": "C3_conversion_pct", "ENB": "ENB_conversion_pct"}.get(monomer, f"{monomer}_conversion_pct")
        if comp_key in kpis:
            rows.append(KPI(f"segment_{segment}_wt", float(kpis.get(comp_key, 0.0)), "wt%", "composition", template.template_id, segment, comp_key, (0.0, 100.0)))
        elif reactor is not None:
            comp = getattr(reactor, "polymer_composition_wt", {}) or {}
            value = positive(comp.get(f"{monomer}_wt", comp.get(f"{segment}_wt", 0.0)))
            rows.append(KPI(f"segment_{segment}_wt", value, "wt%", "composition", template.template_id, segment, comp_key, (0.0, 100.0)))
        if conv_key in kpis:
            rows.append(KPI(f"conversion_{monomer}", float(kpis.get(conv_key, 0.0)), "%", "conversion", template.template_id, monomer, conv_key, (0.0, 100.0)))
    for name, unit, category, bounds in [
        ("polymer_kg_h", "kg/h", "production", (0.0, None)),
        ("heat_duty_kW", "kW", "energy", (0.0, None)),
        ("solids_wt", "wt%", "fluid", (0.0, 100.0)),
        ("dynamic_viscosity_Pa_s", "Pa.s", "fluid", (0.0, None)),
        ("fouling_index", "-", "risk", (0.0, None)),
        ("ENB_residue_ppm", "ppm", "recovery", (0.0, None)),
    ]:
        if name in kpis:
            rows.append(KPI(name, float(kpis.get(name, 0.0)), unit, category, template.template_id, "", name, bounds))
    for warning in warnings:
        rows.append(KPI("template_warning", warning, "-", "warning", template.template_id, "", "", (None, None), warning))
    return validate_kpi_bounds(rows)


def epdm_compatibility_kpis(kpis: list[KPI]) -> dict[str, float]:
    """Return EPDM-compatible KPI aliases from normalized KPI rows."""
    output: dict[str, float] = {}
    for kpi in kpis:
        if kpi.compatibility_alias and isinstance(kpi.value, (int, float)):
            output[kpi.compatibility_alias] = float(kpi.value)
    return output


__all__ = ["KPI", "build_template_kpis", "epdm_compatibility_kpis", "validate_kpi_bounds", "kpis_to_dataframe"]
