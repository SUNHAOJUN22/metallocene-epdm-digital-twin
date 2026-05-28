"""Physical penalty terms for residual-constrained estimation."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def physical_penalty(value: float, lower: float, upper: float, *, weight: float = 1.0) -> float:
    """Return a quadratic penalty outside physical bounds."""
    val, lo, hi = float(value), float(lower), float(upper)
    if hi < lo:
        raise ValueError("upper bound must be >= lower bound")
    if lo <= val <= hi:
        return 0.0
    distance = lo - val if val < lo else val - hi
    return float(weight) * float(distance * distance)


def physical_penalty_breakdown(parameters: dict[str, float], bounds: dict[str, tuple[float, float]]) -> pd.DataFrame:
    """Return parameter-level physical penalties."""
    rows: list[dict[str, Any]] = []
    for name, value in parameters.items():
        lo, hi = bounds.get(name, (-np.inf, np.inf))
        penalty = physical_penalty(float(value), float(lo), float(hi))
        rows.append({"parameter": name, "value": float(value), "lower": float(lo), "upper": float(hi), "penalty": penalty, "passed": penalty == 0.0})
    return pd.DataFrame(rows)
