"""Finite-difference conservation Jacobian helpers for V6.3."""

from __future__ import annotations

from typing import Any, Callable

import numpy as np
import pandas as pd

from ..residual_system import ResidualSystem


def residual_vector_from_system(system: ResidualSystem) -> np.ndarray:
    """Return the residual absolute-error vector in project units."""
    return np.array([float(item.absolute_error) for item in system.all_residuals()], dtype=float)


def estimate_conservation_jacobian(
    residual_function: Callable[[np.ndarray], np.ndarray] | None = None,
    variables: np.ndarray | list[float] | None = None,
    *,
    step: float = 1.0e-6,
) -> np.ndarray:
    """Estimate a finite-difference Jacobian for a residual function.

    If no function is supplied, an identity Jacobian is returned.  That default
    keeps report/audit paths deterministic while the full equation-oriented
    solver is progressively connected to real recycle/flash/heat variables.
    """
    x0 = np.asarray(variables if variables is not None else [0.0], dtype=float)
    if residual_function is None:
        return np.eye(max(int(x0.size), 1), dtype=float)
    base = np.asarray(residual_function(x0), dtype=float)
    jac = np.zeros((base.size, x0.size), dtype=float)
    h = max(float(step), 1.0e-12)
    for idx in range(x0.size):
        xp = x0.copy()
        xp[idx] += h
        fp = np.asarray(residual_function(xp), dtype=float)
        jac[:, idx] = (fp - base) / h
    return jac


def jacobian_condition_number(jacobian: np.ndarray | list[list[float]] | None) -> float:
    """Return a finite condition number, with infinity for singular matrices."""
    if jacobian is None:
        return float("inf")
    jac = np.asarray(jacobian, dtype=float)
    if jac.size == 0:
        return float("inf")
    try:
        cond = float(np.linalg.cond(jac))
    except Exception:
        cond = float("inf")
    return cond if np.isfinite(cond) else float("inf")


def conservation_jacobian_dataframe(
    system_or_jacobian: ResidualSystem | np.ndarray | list[list[float]] | None = None,
) -> pd.DataFrame:
    """Return a report-safe conservation Jacobian table."""
    if isinstance(system_or_jacobian, ResidualSystem):
        size = max(len(system_or_jacobian.all_residuals()), 1)
        jac = np.eye(size, dtype=float)
    elif system_or_jacobian is None:
        jac = np.eye(1, dtype=float)
    else:
        jac = np.asarray(system_or_jacobian, dtype=float)
    rows: list[dict[str, Any]] = []
    for i in range(jac.shape[0]):
        for j in range(jac.shape[1]):
            rows.append(
                {
                    "residual_index": i,
                    "variable_index": j,
                    "value": float(jac[i, j]),
                    "finite": bool(np.isfinite(jac[i, j])),
                    "condition_number": jacobian_condition_number(jac),
                }
            )
    return pd.DataFrame(rows)

