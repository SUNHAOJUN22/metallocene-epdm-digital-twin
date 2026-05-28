"""Solver certificate generation for V6.0 audit reports."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from ..residual_solver import residual_acceptance_summary
from ..residual_system import ResidualSystem, build_flowsheet_residual_system


def _system(result_or_system: Any) -> ResidualSystem:
    if isinstance(result_or_system, ResidualSystem):
        return result_or_system
    embedded = getattr(result_or_system, "residual_system", None)
    if isinstance(embedded, ResidualSystem):
        return embedded
    return build_flowsheet_residual_system(result_or_system)


def generate_solver_certificate(result_or_system: Any, *, solver_id: str = "residual_constrained_solver") -> dict[str, Any]:
    """Return a finite certificate for residual-aware solver acceptance."""
    system = _system(result_or_system)
    summary = residual_acceptance_summary(system)
    residual_norm = float(sum(item.absolute_error for item in system.all_residuals()))
    violations = int(summary["critical_count"])
    accepted = bool(summary["passed"] and violations == 0 and np.isfinite(residual_norm))
    return {
        "solver_id": solver_id,
        "solver_certificate_passed": accepted,
        "residual_norm": residual_norm,
        "constraint_violations": violations,
        "overall_score": float(summary["overall_score"]),
        "fallback_reason": "" if accepted else "residual acceptance failed",
    }


def solver_certificate_dataframe(result_or_system: Any) -> pd.DataFrame:
    """Return solver certificate as a DataFrame."""
    return pd.DataFrame([generate_solver_certificate(result_or_system)])
