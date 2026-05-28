"""Balance-law helpers for the V6.0 industrial math core."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from ..residual_system import ResidualSystem, build_flowsheet_residual_system


def accumulation_identity(
    accumulation: float,
    input_rate: float,
    output_rate: float,
    generation_rate: float = 0.0,
    consumption_rate: float = 0.0,
) -> dict[str, Any]:
    """Evaluate accumulation = input - output + generation - consumption."""
    lhs = float(accumulation)
    rhs = float(input_rate) - float(output_rate) + float(generation_rate) - float(consumption_rate)
    error = lhs - rhs
    return {
        "equation": "accumulation = input - output + generation - consumption",
        "lhs": lhs,
        "rhs": rhs,
        "absolute_error": abs(error),
        "passed": bool(np.isfinite(error) and abs(error) <= 1.0e-9),
        "unit": "rate basis",
    }


def _system_from_result(result_or_system: Any) -> ResidualSystem:
    if isinstance(result_or_system, ResidualSystem):
        return result_or_system
    embedded = getattr(result_or_system, "residual_system", None)
    if isinstance(embedded, ResidualSystem):
        return embedded
    return build_flowsheet_residual_system(result_or_system)


def balance_law_records(result_or_system: Any) -> pd.DataFrame:
    """Return mass, component, phase, reaction and energy balance records."""
    system = _system_from_result(result_or_system)
    rows = []
    for group, residuals in [
        ("mass", system.mass_residuals),
        ("component", system.component_residuals),
        ("energy", system.energy_residuals),
        ("phase", system.phase_residuals),
        ("reaction", system.reaction_residuals),
        ("numerical", system.numerical_residuals),
    ]:
        for residual in residuals:
            row = residual.as_dict()
            row["balance_group"] = group
            row["balance_law_coupled"] = bool(residual.equation and residual.unit)
            rows.append(row)
    return pd.DataFrame(rows)


def balance_law_acceptance(result_or_system: Any, *, minimum_score: float = 70.0) -> dict[str, Any]:
    """Return compact balance-law acceptance diagnostics."""
    system = _system_from_result(result_or_system)
    df = balance_law_records(system)
    if df.empty:
        return {"passed": False, "rows": 0, "overall_score": 0.0, "critical_count": 1}
    hard = df[df["severity"].astype(str).isin(["error", "critical"])]
    failed = hard[~hard["passed"].astype(bool)]
    return {
        "passed": bool(failed.empty and system.overall_score >= minimum_score),
        "rows": int(len(df)),
        "overall_score": float(system.overall_score),
        "critical_count": int(df["severity"].astype(str).eq("critical").sum()),
        "failed_hard_count": int(len(failed)),
    }
