"""Equation-residual-code coupling checks for V5.7."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd

from .equation_binding import equation_binding_dataframe, run_equation_binding_checks
from .equation_reverse_check import run_equation_reverse_checks


@dataclass(frozen=True)
class EquationResidualCoupling:
    """One equation-code-residual coupling record."""

    equation_id: str
    implementation_function: str
    benchmark_id: str
    residual_id: str
    dimensional_signature: str
    trend_check_passed: bool
    reverse_check_passed: bool
    residual_coupled: bool
    passed: bool
    diagnostic: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def equation_residual_coupling_dataframe() -> pd.DataFrame:
    """Return critical equation to residual coupling records."""
    bindings = equation_binding_dataframe()
    binding_checks = run_equation_binding_checks()
    reverse_checks = run_equation_reverse_checks()
    rows: list[EquationResidualCoupling] = []
    for _, row in bindings.iterrows():
        equation_id = str(row.get("equation_id", ""))
        b_row = binding_checks[binding_checks["equation_id"].astype(str) == equation_id]
        r_row = reverse_checks[reverse_checks["equation_id"].astype(str) == equation_id]
        trend_passed = bool(not b_row.empty and b_row["passed"].astype(bool).all())
        reverse_passed = bool(not r_row.empty and r_row["passed"].astype(bool).all())
        residual_id = str(row.get("residual_id", ""))
        benchmark_id = str(row.get("benchmark_id", ""))
        signature = str(row.get("dimensional_signature", ""))
        residual_coupled = bool(residual_id and residual_id.lower() not in {"nan", "none"})
        passed = bool(trend_passed and reverse_passed and residual_coupled and benchmark_id and signature)
        rows.append(
            EquationResidualCoupling(
                equation_id=equation_id,
                implementation_function=str(row.get("implementation_function", "")),
                benchmark_id=benchmark_id,
                residual_id=residual_id,
                dimensional_signature=signature,
                trend_check_passed=trend_passed,
                reverse_check_passed=reverse_passed,
                residual_coupled=residual_coupled,
                passed=passed,
                diagnostic="equation, code, benchmark and residual are coupled" if passed else "missing equation-code-residual coupling metadata",
            )
        )
    return pd.DataFrame([item.as_dict() for item in rows])


def equation_residual_coupling_summary() -> dict[str, Any]:
    """Return compact release-gate summary for equation-residual coupling."""
    df = equation_residual_coupling_dataframe()
    if df.empty:
        return {"passed": False, "rows": 0, "failed": 0}
    failed = int((~df["passed"].astype(bool)).sum())
    return {"passed": failed == 0, "rows": int(len(df)), "failed": failed}


def residual_sources_for_equations() -> dict[str, str]:
    """Return equation_id -> residual_id mapping for diagnostics."""
    df = equation_residual_coupling_dataframe()
    if df.empty:
        return {}
    return {str(row["equation_id"]): str(row["residual_id"]) for _, row in df.iterrows()}

