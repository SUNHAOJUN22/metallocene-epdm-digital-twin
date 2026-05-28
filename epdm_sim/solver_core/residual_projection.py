"""Residual projection and acceptance helpers."""

from __future__ import annotations

from typing import Any

from ..residual_objective import residual_objective_score


def bounded_residual_projection(value: float, correction: float, *, max_relative_correction: float = 0.02) -> dict[str, Any]:
    """Apply a bounded correction and report whether it is physically small."""
    value_f = float(value)
    correction_f = float(correction)
    denom = max(abs(value_f), 1.0e-12)
    rel = abs(correction_f) / denom
    accepted = rel <= max_relative_correction
    applied = correction_f if accepted else 0.0
    return {
        "original": value_f,
        "correction": correction_f,
        "corrected": value_f + applied,
        "relative_correction": rel,
        "accepted": accepted,
        "severity": "ok" if accepted else "critical",
    }


def residual_projection_penalty(result_or_system: Any) -> float:
    """Return the residual objective score as a projection penalty."""
    return residual_objective_score(result_or_system)

