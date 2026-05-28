"""Numerical stability helpers shared by model governance layers."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

from .utils import TINY


def finite_or_default(value: Any, default: float = 0.0) -> float:
    """Return a finite float or a default value."""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return float(default)
    return numeric if math.isfinite(numeric) else float(default)


def nonnegative(value: Any, default: float = 0.0) -> float:
    """Return a finite non-negative float."""
    return max(finite_or_default(value, default), 0.0)


def bounded(value: Any, low: float, high: float, default: float | None = None) -> float:
    """Return a finite value clipped to [low, high]."""
    if high < low:
        raise ValueError("high must be greater than or equal to low")
    numeric = finite_or_default(value, low if default is None else default)
    return min(max(numeric, low), high)


def normalize_to_sum(values: Mapping[str, float] | Sequence[float], target: float = 1.0):
    """Normalize a mapping or sequence to a target sum."""
    if isinstance(values, Mapping):
        clean = {key: max(finite_or_default(value), 0.0) for key, value in values.items()}
        total = sum(clean.values())
        if total <= TINY:
            return {key: 0.0 for key in clean}
        return {key: value * target / total for key, value in clean.items()}
    clean_values = [max(finite_or_default(value), 0.0) for value in values]
    total = sum(clean_values)
    if total <= TINY:
        return [0.0 for _ in clean_values]
    return [value * target / total for value in clean_values]


def safe_exp(x: Any, lower: float = -80.0, upper: float = 80.0) -> float:
    """Return exp(x) with bounded exponent."""
    return math.exp(bounded(x, lower, upper, 0.0))


def safe_log(x: Any, floor: float = 1.0e-12) -> float:
    """Return log(max(x, floor)) with finite protection."""
    return math.log(max(finite_or_default(x, floor), floor))


def safe_power(base: Any, exponent: Any, default: float = 0.0) -> float:
    """Return a finite power result or default."""
    try:
        value = finite_or_default(base, default) ** finite_or_default(exponent, 1.0)
    except Exception:
        return float(default)
    try:
        return float(value) if math.isfinite(float(value)) else float(default)
    except (TypeError, ValueError):
        return float(default)


def finite_dict(payload: Mapping[str, Any], default: float = 0.0) -> dict[str, Any]:
    """Replace non-finite numeric values inside a flat mapping."""
    clean: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, bool) or isinstance(value, str) or value is None:
            clean[key] = value
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            clean[key] = value
            continue
        clean[key] = numeric if math.isfinite(numeric) else float(default)
    return clean


def validate_kpi_finiteness(kpis: Mapping[str, Any]) -> list[str]:
    """Return KPI keys with non-finite numeric values."""
    bad: list[str] = []
    for key, value in kpis.items():
        if isinstance(value, bool) or isinstance(value, str) or value is None:
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(numeric):
            bad.append(key)
    return bad
