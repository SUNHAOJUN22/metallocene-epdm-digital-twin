"""Bounded numerical update helpers."""

from __future__ import annotations

from typing import Iterable

import numpy as np


def project_nonnegative(values: Iterable[float], *, floor: float = 0.0) -> np.ndarray:
    """Project finite numeric values to a nonnegative lower bound."""
    arr = np.asarray(list(values), dtype=float)
    arr = np.where(np.isfinite(arr), arr, floor)
    return np.maximum(arr, float(floor))


def bounded_explicit_step(state: Iterable[float], derivative: Iterable[float], dt: float, *, floor: float = 0.0) -> np.ndarray:
    """Return one explicit step with finite nonnegative projection."""
    state_arr = np.asarray(list(state), dtype=float)
    deriv_arr = np.asarray(list(derivative), dtype=float)
    if state_arr.shape != deriv_arr.shape:
        raise ValueError("state and derivative must have the same shape")
    return project_nonnegative(state_arr + float(dt) * deriv_arr, floor=floor)

