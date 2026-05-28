"""Unified V5.7 model-acceptance helpers."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .constraints import physical_constraints_acceptance
from .equations import equation_kernel_acceptance
from .residuals import residual_kernel_acceptance


def math_core_acceptance(result_or_system: Any, *, config: Any | None = None) -> dict[str, Any]:
    """Return combined equation/residual/constraint acceptance."""
    eq = equation_kernel_acceptance()
    residual = residual_kernel_acceptance(result_or_system)
    constraints = physical_constraints_acceptance(result_or_system, config=config)
    passed = bool(eq["passed"] and residual["passed"] and constraints["passed"])
    return {
        "passed": passed,
        "equation_passed": bool(eq["passed"]),
        "residual_passed": bool(residual["passed"]),
        "constraints_passed": bool(constraints["passed"]),
        "residual_objective_score": float(residual["residual_objective_score"]),
    }


def math_core_acceptance_dataframe(result_or_system: Any, *, config: Any | None = None) -> pd.DataFrame:
    """Return combined math-core acceptance as a one-row DataFrame."""
    return pd.DataFrame([math_core_acceptance(result_or_system, config=config)])

