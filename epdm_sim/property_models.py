"""Template-dispatched polymer property models.

The V4.5 property layer keeps EPDM empirical outputs compatible while exposing
a generic dispatch interface for future solution copolymer templates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import math
import pandas as pd

from .reaction_templates import property_model_from_template, template_with_fallback
from .utils import TINY, clamp, positive, safe_divide


@dataclass(frozen=True)
class PolymerPropertyResult:
    """Template-dispatched polymer property result."""

    template_id: str
    property_model_id: str
    composition_wt: dict[str, float]
    Mw: float
    Mn: float
    PDI: float
    Mooney: float
    Tg_C: float
    Tm_C: float | None
    crystallization_risk: str
    fouling_index: float
    fouling_risk: str
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        """Return report-friendly flat values."""
        row = {
            "template_id": self.template_id,
            "property_model_id": self.property_model_id,
            "Mw": self.Mw,
            "Mn": self.Mn,
            "PDI": self.PDI,
            "Mooney": self.Mooney,
            "Tg_C": self.Tg_C,
            "Tm_C": self.Tm_C,
            "crystallization_risk": self.crystallization_risk,
            "fouling_index": self.fouling_index,
            "fouling_risk": self.fouling_risk,
            "warnings": "; ".join(self.warnings),
        }
        row.update({f"{key}_wt": value for key, value in self.composition_wt.items()})
        return row

    def as_dataframe(self) -> pd.DataFrame:
        """Return the result as a one-row DataFrame."""
        return pd.DataFrame([self.as_dict()])


def _normalize_composition(composition: dict[str, float]) -> tuple[dict[str, float], list[str]]:
    warnings: list[str] = []
    clean = {key: positive(float(value)) for key, value in composition.items()}
    total = sum(clean.values())
    if total <= TINY:
        warnings.append("Composition sum is zero; using an equal-segment fallback.")
        if not clean:
            clean = {"A": 100.0}
        total = sum(clean.values())
    if abs(total - 100.0) > 1.0:
        warnings.append(f"Composition sums to {total:.3g} wt%, normalized to 100 wt%.")
    return {key: 100.0 * value / max(total, TINY) for key, value in clean.items()}, warnings


def predict_polymer_properties(
    template_id: str,
    composition: dict[str, float],
    Mw: float,
    PDI: float,
    process_conditions: dict[str, float] | None = None,
    params: dict[str, Any] | None = None,
) -> PolymerPropertyResult:
    """Dispatch polymer property prediction by reaction-template property model."""
    template, template_warnings = template_with_fallback(template_id)
    model = property_model_from_template(template.template_id)
    conditions = process_conditions or {}
    composition_wt, warnings = _normalize_composition(composition)
    warnings.extend(template_warnings)
    Mw_safe = positive(float(Mw), 50000.0)
    PDI_safe = max(float(PDI), 1.0)
    if PDI < 1.0:
        warnings.append("PDI < 1 is nonphysical; clipped to 1.0.")
    model_id = str(model.get("model_id", "generic_solution_polymer_v1"))
    if model_id.startswith("epdm"):
        return _predict_epdm_properties(template.template_id, model_id, composition_wt, Mw_safe, PDI_safe, conditions, warnings)
    return _predict_generic_properties(template.template_id, model_id, composition_wt, Mw_safe, PDI_safe, conditions, warnings)


def _predict_epdm_properties(
    template_id: str,
    model_id: str,
    composition_wt: dict[str, float],
    Mw: float,
    PDI: float,
    conditions: dict[str, float],
    warnings: list[str],
) -> PolymerPropertyResult:
    from .polymer_props import estimate_mooney, estimate_tg, estimate_tm_and_crystallinity, fouling_risk_index

    C2 = composition_wt.get("ethylene", composition_wt.get("C2", composition_wt.get("E", 0.0)))
    C3 = composition_wt.get("propylene", composition_wt.get("C3", composition_wt.get("P", 0.0)))
    ENB = composition_wt.get("ENB", composition_wt.get("D", 0.0))
    mooney = estimate_mooney(Mw, PDI, C2, ENB)
    tg = estimate_tg(C2, C3, ENB)
    tm, crystal = estimate_tm_and_crystallinity(C2, C3)
    fouling, fouling_level = fouling_risk_index(
        float(conditions.get("solids_wt", 10.0)),
        Mw,
        PDI,
        C2,
        float(conditions.get("temperature_K", 373.15)),
        mooney,
    )
    return PolymerPropertyResult(template_id, model_id, composition_wt, Mw, Mw / PDI, PDI, mooney, tg, tm, crystal, fouling, fouling_level, warnings)


def _predict_generic_properties(
    template_id: str,
    model_id: str,
    composition_wt: dict[str, float],
    Mw: float,
    PDI: float,
    conditions: dict[str, float],
    warnings: list[str],
) -> PolymerPropertyResult:
    """Generic finite property proxy for uncalibrated solution polymer templates."""
    fractions = {key: value / 100.0 for key, value in composition_wt.items()}
    segment_tg = {"A": 240.0, "B": 260.0, "C": 280.0, "monomer_A": 240.0, "monomer_B": 260.0, "monomer_C": 280.0}
    reciprocal = sum(fractions[key] / segment_tg.get(key, 260.0) for key in fractions)
    Tg_C = safe_divide(1.0, reciprocal, 260.0) - 273.15
    Mooney = clamp(math.exp(2.4 + 0.65 * math.log(max(Mw, 1000.0) / 100000.0) + 0.05 * PDI), 2.0, 500.0)
    solids = float(conditions.get("solids_wt", 10.0))
    fouling = (positive(solids) / 20.0) ** 2 * (Mw / 300000.0) ** 0.55
    level = "low" if fouling < 1.0 else "medium" if fouling < 3.0 else "high"
    warnings.append("Generic property model is a positive finite proxy and requires system-specific calibration.")
    return PolymerPropertyResult(template_id, model_id, composition_wt, Mw, Mw / PDI, PDI, Mooney, Tg_C, None, "not evaluated", fouling, level, warnings)


def property_models_dataframe() -> pd.DataFrame:
    """Return available template property models as a table."""
    from .reaction_templates import load_reaction_templates

    rows = []
    for template_id, template in load_reaction_templates().items():
        model = property_model_from_template(template_id)
        rows.append({"template_id": template_id, **model})
    return pd.DataFrame(rows)
