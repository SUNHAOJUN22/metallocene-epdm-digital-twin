"""Constrained residual-aware solver helpers for V6.0."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd

from ..residual_solver import residual_acceptance_summary, residual_correction_trace_dataframe
from ..residual_system import ResidualSystem, build_flowsheet_residual_system
from .solver_certificates import generate_solver_certificate


@dataclass(frozen=True)
class ConstrainedSolveResult:
    """Result from a bounded residual-constrained solve/certification pass."""

    solver_id: str
    accepted: bool
    residual_norm: float
    constraint_violations: int
    fallback_reason: str
    correction_rows: int

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _system(result_or_system: Any) -> ResidualSystem:
    if isinstance(result_or_system, ResidualSystem):
        return result_or_system
    embedded = getattr(result_or_system, "residual_system", None)
    if isinstance(embedded, ResidualSystem):
        return embedded
    return build_flowsheet_residual_system(result_or_system)


def minimize_residual_subject_to_bounds(value: float, lower: float, upper: float, residual_penalty: float = 0.0) -> dict[str, Any]:
    """Project a scalar into bounds and report residual penalty."""
    lo, hi = float(lower), float(upper)
    if hi < lo:
        raise ValueError("upper bound must be >= lower bound")
    projected = float(np.clip(float(value), lo, hi))
    return {
        "original": float(value),
        "projected": projected,
        "lower": lo,
        "upper": hi,
        "residual_penalty": max(float(residual_penalty), 0.0),
        "passed": bool(lo <= projected <= hi and np.isfinite(projected)),
    }


def solve_with_mass_energy_constraints(result_or_system: Any) -> ConstrainedSolveResult:
    """Return a constrained solve certificate from existing residuals.

    This helper is intentionally read-only: it certifies whether existing
    residuals can be accepted and records correction diagnostics without
    hiding large physical-balance errors.
    """
    system = _system(result_or_system)
    summary = residual_acceptance_summary(system)
    residual_norm = float(100.0 - float(summary["overall_score"]))
    violations = int(summary["critical_count"])
    corrections = residual_correction_trace_dataframe()
    accepted = bool(summary["passed"] and violations == 0)
    return ConstrainedSolveResult(
        solver_id="mass_energy_constrained_certificate",
        accepted=accepted,
        residual_norm=residual_norm,
        constraint_violations=violations,
        fallback_reason="" if accepted else "critical residual or low residual score",
        correction_rows=int(len(corrections)),
    )


def constrained_solver_dataframe(result_or_system: Any) -> pd.DataFrame:
    """Return constrained solver status and certificate fields."""
    result = solve_with_mass_energy_constraints(result_or_system)
    certificate = generate_solver_certificate(result_or_system, solver_id=result.solver_id)
    return pd.DataFrame([{**result.as_dict(), **certificate}])
