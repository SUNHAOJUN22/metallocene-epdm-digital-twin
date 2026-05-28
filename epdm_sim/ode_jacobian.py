"""Finite-difference Jacobian helpers for template ODE stiff solvers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

from .ode_scaling import scale_state_vector, unscale_state_vector


@dataclass(frozen=True)
class JacobianDiagnostic:
    """Small diagnostic summary for a finite-difference Jacobian."""

    shape: tuple[int, int]
    finite: bool
    max_abs: float
    condition_proxy: float

    def as_dict(self) -> dict[str, object]:
        return {
            "shape": self.shape,
            "finite": self.finite,
            "max_abs": self.max_abs,
            "condition_proxy": self.condition_proxy,
        }


def finite_difference_jacobian(
    rhs: Callable[[float, np.ndarray], np.ndarray],
    t: float,
    y: np.ndarray,
    *,
    rel_step: float = 1.0e-6,
    abs_step: float = 1.0e-8,
) -> np.ndarray:
    """Return a central finite-difference Jacobian for dy/dt=f(t,y).

    The implementation is intentionally conservative: perturbations are based
    on variable magnitudes and outputs are forced finite so a failed local
    derivative cannot poison the stiff solver.
    """
    y0 = np.asarray(y, dtype=float)
    f0 = np.asarray(rhs(t, y0), dtype=float)
    jac = np.zeros((f0.size, y0.size), dtype=float)
    for idx in range(y0.size):
        h = max(abs_step, rel_step * max(abs(y0[idx]), 1.0))
        y_plus = y0.copy()
        y_minus = y0.copy()
        y_plus[idx] += h
        y_minus[idx] -= h
        try:
            f_plus = np.asarray(rhs(t, y_plus), dtype=float)
            f_minus = np.asarray(rhs(t, y_minus), dtype=float)
            column = (f_plus - f_minus) / (2.0 * h)
        except Exception:
            column = np.zeros_like(f0)
        jac[:, idx] = np.nan_to_num(column, nan=0.0, posinf=0.0, neginf=0.0)
    return jac


def scaled_finite_difference_jacobian(
    rhs_unscaled: Callable[[float, np.ndarray], np.ndarray],
    t: float,
    y_scaled: np.ndarray,
    scales: np.ndarray,
) -> np.ndarray:
    """Return Jacobian for a scaled state vector y_scaled=y/scales."""
    scale = np.asarray(scales, dtype=float)

    def rhs_scaled(t_local: float, ys: np.ndarray) -> np.ndarray:
        y_unscaled = unscale_state_vector(ys, scale)
        dy_unscaled = np.asarray(rhs_unscaled(t_local, y_unscaled), dtype=float)
        return scale_state_vector(dy_unscaled, scale)

    return finite_difference_jacobian(rhs_scaled, t, np.asarray(y_scaled, dtype=float))


def jacobian_diagnostic(jacobian: np.ndarray) -> JacobianDiagnostic:
    """Return finite/size diagnostics without expensive exact conditioning."""
    jac = np.asarray(jacobian, dtype=float)
    finite = bool(np.isfinite(jac).all())
    max_abs = float(np.nanmax(np.abs(jac))) if jac.size else 0.0
    row_norm = np.linalg.norm(jac, ord=np.inf) if jac.size else 0.0
    col_norm = np.linalg.norm(jac, ord=1) if jac.size else 0.0
    condition_proxy = float(max(row_norm * col_norm, 0.0))
    return JacobianDiagnostic(tuple(jac.shape), finite, max_abs, condition_proxy)
