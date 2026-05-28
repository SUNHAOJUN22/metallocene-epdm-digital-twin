"""Shared utilities and unit conversions for the EPDM simulator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import yaml

R_GAS = 8.314462618
TINY = 1.0e-12

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"


def data_path(filename: str) -> Path:
    """Return an absolute path inside the project data directory."""
    return DATA_DIR / filename


def load_json(path: str | Path) -> Any:
    """Load JSON from a local file."""
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_yaml(path: str | Path) -> dict[str, Any]:
    """Load YAML from a local file."""
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def write_json(path: str | Path, payload: Any) -> None:
    """Write JSON using UTF-8 encoding."""
    with Path(path).open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def clamp(value: float, lower: float, upper: float) -> float:
    """Clamp a numeric value to a closed interval."""
    return max(lower, min(upper, value))


def positive(value: float, floor: float = 0.0) -> float:
    """Return value if finite and above floor, otherwise floor."""
    try:
        if value != value:
            return floor
        return max(float(value), floor)
    except (TypeError, ValueError):
        return floor


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Divide with a stable default for near-zero denominators."""
    if abs(denominator) < TINY:
        return default
    return numerator / denominator


def kg_h_to_mol_h(mass_kg_h: float, mw_g_mol: float) -> float:
    """Convert kg/h to mol/h using molecular weight in g/mol."""
    return positive(mass_kg_h) * 1000.0 / max(mw_g_mol, TINY)


def mol_h_to_kg_h(mol_h: float, mw_g_mol: float) -> float:
    """Convert mol/h to kg/h using molecular weight in g/mol."""
    return positive(mol_h) * mw_g_mol / 1000.0


def normalize(values: Mapping[str, float]) -> dict[str, float]:
    """Normalize non-negative mapping values to sum to one."""
    clean = {key: positive(value) for key, value in values.items()}
    total = sum(clean.values())
    if total <= TINY:
        return {key: 0.0 for key in clean}
    return {key: value / total for key, value in clean.items()}


def weighted_average(values: Mapping[str, float], weights: Mapping[str, float], default: float = 0.0) -> float:
    """Return a weighted average across common keys."""
    total = 0.0
    denom = 0.0
    for key, weight in weights.items():
        if key in values:
            clean_weight = positive(weight)
            total += values[key] * clean_weight
            denom += clean_weight
    return safe_divide(total, denom, default)


def c_to_k(temperature_C: float) -> float:
    """Convert Celsius to Kelvin."""
    return float(temperature_C) + 273.15


def k_to_c(temperature_K: float) -> float:
    """Convert Kelvin to Celsius."""
    return float(temperature_K) - 273.15


def mpa_to_pa(pressure_MPa: float) -> float:
    """Convert MPa to Pa."""
    return float(pressure_MPa) * 1.0e6


def pa_to_mpa(pressure_Pa: float) -> float:
    """Convert Pa to MPa."""
    return float(pressure_Pa) / 1.0e6


def mid_range(low: float, high: float) -> float:
    """Return midpoint of a numeric range."""
    return 0.5 * (float(low) + float(high))


def engineering_error_percent(reference: float, actual: float) -> float:
    """Return signed percentage closure error with stable near-zero handling."""
    return 100.0 * safe_divide(actual - reference, max(abs(reference), TINY), 0.0)


def model_dump_compat(model: Any) -> dict[str, Any]:
    """Return a Pydantic model dict in a v1/v2 compatible way."""
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()
