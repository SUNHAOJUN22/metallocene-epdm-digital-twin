"""Residual-level math-kernel helpers."""

from __future__ import annotations

from typing import Any

import pandas as pd

from ..residual_objective import residual_diagnostics_dataframe, residual_objective_score
from ..residual_system import ResidualSystem, build_flowsheet_residual_system, residual_system_acceptance


def coerce_residual_system(result_or_system: Any) -> ResidualSystem:
    """Return a residual system from a result or residual-system object."""
    if isinstance(result_or_system, ResidualSystem):
        return result_or_system
    embedded = getattr(result_or_system, "residual_system", None)
    if isinstance(embedded, ResidualSystem):
        return embedded
    return build_flowsheet_residual_system(result_or_system)


def residual_kernel_dataframe(result_or_system: Any) -> pd.DataFrame:
    """Return detailed residual diagnostics for math-core gates."""
    return residual_diagnostics_dataframe(coerce_residual_system(result_or_system))


def residual_kernel_acceptance(result_or_system: Any, *, minimum_score: float = 70.0) -> dict[str, Any]:
    """Return residual acceptance with objective penalty."""
    system = coerce_residual_system(result_or_system)
    acceptance = residual_system_acceptance(system, minimum_score=minimum_score)
    acceptance["residual_objective_score"] = residual_objective_score(system)
    return acceptance

