"""Top-level diagnostics for the layered V5.7 math core."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .acceptance import math_core_acceptance
from .constraints import physical_constraints_dataframe
from .equations import equation_kernel_dataframe
from .residuals import residual_kernel_dataframe


def math_core_diagnostics_dataframe(result_or_system: Any, *, config: Any | None = None) -> pd.DataFrame:
    """Return compact diagnostics across equations, residuals and constraints."""
    acceptance = math_core_acceptance(result_or_system, config=config)
    return pd.DataFrame(
        [
            {"domain": "equations", "rows": len(equation_kernel_dataframe()), "passed": acceptance["equation_passed"]},
            {"domain": "residuals", "rows": len(residual_kernel_dataframe(result_or_system)), "passed": acceptance["residual_passed"]},
            {"domain": "constraints", "rows": len(physical_constraints_dataframe(result_or_system, config=config)), "passed": acceptance["constraints_passed"]},
        ]
    )

