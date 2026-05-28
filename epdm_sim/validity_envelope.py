"""Model validity-envelope checks for extrapolation governance.

The checks are intentionally lightweight and deterministic.  They do not
replace model-specific preflight validation; they classify whether current
inputs are comfortably inside, near the edge of, or outside the R&D screening
range declared by the registry/template/data layers.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any

import pandas as pd

from .flowsheet import ProcessConfig
from .model_registry import load_model_registry
from .property_confidence import property_confidence_dataframe
from .reaction_templates import template_with_fallback
from .utils import model_dump_compat


@dataclass(frozen=True)
class ValidityEnvelopeResult:
    """One validity-envelope classification row."""

    model_id: str
    variable: str
    value: float | str
    valid_range: str
    status: str
    severity: str
    message: str
    suggested_fix: str = ""

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


DEFAULT_RANGES: dict[str, tuple[float, float]] = {
    "temperature_C": (60.0, 180.0),
    "pressure_MPa": (0.1, 5.0),
    "solids_wt": (0.0, 35.0),
    "Mw": (5.0e4, 2.0e6),
    "PDI": (1.0, 8.0),
    "agitation_rpm": (0.0, 1500.0),
    "residence_time_min": (1.0, 180.0),
    "pipe_diameter_m": (0.003, 0.3),
    "pipe_length_m": (0.1, 500.0),
    "shear_rate_s": (0.01, 1.0e5),
    "solvent_mass_kg_h": (0.1, 1.0e5),
    "ethylene_kg_h": (0.0, 1.0e5),
    "propylene_kg_h": (0.0, 1.0e5),
    "enb_kg_h": (0.0, 1.0e4),
    "hydrogen_g_h": (0.0, 1.0e5),
}


def _parse_range_text(text: Any) -> tuple[float, float] | None:
    """Parse simple registry range text like ``60-180 engineering``."""
    if isinstance(text, (list, tuple)) and len(text) == 2:
        try:
            return float(text[0]), float(text[1])
        except (TypeError, ValueError):
            return None
    if not isinstance(text, str):
        return None
    match = re.search(r"(-?\d+(?:\.\d+)?)\s*[-–]\s*(-?\d+(?:\.\d+)?)", text)
    if not match:
        return None
    low, high = float(match.group(1)), float(match.group(2))
    return (min(low, high), max(low, high))


def registry_validity_ranges(model_id: str = "flowsheet") -> dict[str, tuple[float, float]]:
    """Return numeric validity ranges parsed from model_registry plus defaults."""
    ranges = dict(DEFAULT_RANGES)
    try:
        registry = load_model_registry()
        modules = registry.get("modules", []) if isinstance(registry, dict) else []
        for item in modules:
            if item.get("module_id") != model_id:
                continue
            for key, value in (item.get("validity_range") or {}).items():
                parsed = _parse_range_text(value)
                if parsed is not None:
                    ranges[key] = parsed
    except Exception:
        pass
    return ranges


def template_validity_ranges(template_id: str = "EPDM_EPM_metallocene_solution") -> dict[str, tuple[float, float]]:
    """Return validity ranges declared by the reaction template."""
    ranges: dict[str, tuple[float, float]] = {}
    template, _ = template_with_fallback(template_id)
    for key, value in (template.validity_range or {}).items():
        parsed = _parse_range_text(value)
        if parsed is not None:
            ranges[key] = parsed
    return ranges


def check_value_against_range(
    model_id: str,
    variable: str,
    value: float | str,
    valid_range: tuple[float, float] | None,
    *,
    near_edge_fraction: float = 0.10,
) -> ValidityEnvelopeResult:
    """Classify one value against a numeric range."""
    if valid_range is None:
        return ValidityEnvelopeResult(model_id, variable, value, "unknown", "unknown", "warning", f"{variable} has no declared validity range.", "Add model_registry or property-source range metadata.")
    low, high = valid_range
    range_text = f"{low:g} to {high:g}"
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return ValidityEnvelopeResult(model_id, variable, value, range_text, "outside", "error", f"{variable} is not numeric.", "Check input type and units.")
    if not math.isfinite(numeric):
        return ValidityEnvelopeResult(model_id, variable, numeric, range_text, "outside", "error", f"{variable} is not finite.", "Replace NaN/inf with a physically meaningful value.")
    if numeric < low or numeric > high:
        return ValidityEnvelopeResult(model_id, variable, numeric, range_text, "outside", "error", f"{variable}={numeric:g} is outside the calibrated/screening range {range_text}.", "Do not extrapolate without validation data; revise operating point or add calibration data.")
    width = max(high - low, 1.0e-12)
    near = numeric - low <= near_edge_fraction * width or high - numeric <= near_edge_fraction * width
    if near:
        return ValidityEnvelopeResult(model_id, variable, numeric, range_text, "near_edge", "warning", f"{variable}={numeric:g} is near the edge of {range_text}.", "Treat predictions as screening estimates and prioritize validation.")
    return ValidityEnvelopeResult(model_id, variable, numeric, range_text, "inside", "ok", f"{variable} is inside validity range.", "")


def run_validity_envelope_for_config(
    config: ProcessConfig | dict[str, Any] | None = None,
    *,
    template_id: str = "EPDM_EPM_metallocene_solution",
    model_id: str = "flowsheet",
) -> list[ValidityEnvelopeResult]:
    """Evaluate validity-envelope status for a process configuration."""
    cfg = config if isinstance(config, ProcessConfig) else ProcessConfig(**(config or {}))
    payload = model_dump_compat(cfg)
    ranges = registry_validity_ranges(model_id)
    ranges.update(template_validity_ranges(template_id))
    variables = [
        "temperature_C",
        "pressure_MPa",
        "residence_time_min",
        "agitation_rpm",
        "pipe_diameter_m",
        "pipe_length_m",
        "solvent_mass_kg_h",
        "ethylene_kg_h",
        "propylene_kg_h",
        "enb_kg_h",
        "hydrogen_g_h",
    ]
    return [check_value_against_range(model_id, variable, payload.get(variable), ranges.get(variable)) for variable in variables]


def property_source_validity_envelope(temperature_C: float = 100.0, pressure_MPa: float = 1.0) -> pd.DataFrame:
    """Return property-source range checks for the current T/P point."""
    rows: list[dict[str, Any]] = []
    props = property_confidence_dataframe()
    for _, row in props.iterrows():
        for variable, value in {"temperature_C": temperature_C, "pressure_MPa": pressure_MPa}.items():
            range_col = "temperature_range" if variable == "temperature_C" else "pressure_range"
            valid_range = _parse_range_text(row.get(range_col))
            result = check_value_against_range(str(row.get("property_id", "property")), variable, value, valid_range)
            rows.append(result.as_dict() | {"component": row.get("component", ""), "property_name": row.get("property_name", "")})
    return pd.DataFrame(rows)


def validity_envelope_dataframe(results: list[ValidityEnvelopeResult] | None = None) -> pd.DataFrame:
    """Return validity-envelope results as a DataFrame."""
    results = run_validity_envelope_for_config() if results is None else results
    return pd.DataFrame([item.as_dict() for item in results])


def validity_score(results: list[ValidityEnvelopeResult] | pd.DataFrame) -> float:
    """Return a 0-100 score penalizing near-edge and outside extrapolation."""
    df = results if isinstance(results, pd.DataFrame) else validity_envelope_dataframe(results)
    if df.empty:
        return 50.0
    penalty = 0.0
    for status in df["status"].astype(str):
        if status == "outside":
            penalty += 25.0
        elif status == "near_edge":
            penalty += 7.5
        elif status == "unknown":
            penalty += 5.0
    return float(max(0.0, min(100.0, 100.0 - penalty)))
