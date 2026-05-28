"""Reverse checks from implementation output back to equation-registry rules."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd

from .equation_binding import equation_binding_dataframe, run_equation_binding_checks, trend_smoke_results


@dataclass(frozen=True)
class EquationReverseCheck:
    """One executable equation reverse-check row."""

    equation_id: str
    implementation_function: str
    check_type: str
    value: float
    unit: str
    passed: bool
    diagnostic: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_equation_reverse_checks() -> pd.DataFrame:
    """Return executable consistency checks for critical equation bindings."""
    bindings = equation_binding_dataframe()
    binding_checks = run_equation_binding_checks()
    trends = trend_smoke_results()
    rows: list[EquationReverseCheck] = []
    trend_pass = bool(not trends.empty and trends["passed"].astype(bool).all())
    for _, row in bindings.iterrows():
        equation_id = str(row.get("equation_id", ""))
        impl = str(row.get("implementation_function", ""))
        binding_row = binding_checks[binding_checks["equation_id"].astype(str) == equation_id]
        metadata_ok = bool(
            not binding_row.empty
            and binding_row[["has_units", "has_dimensional_signature", "has_benchmark", "has_residual_id"]].astype(bool).all(axis=None)
        )
        import_ok = bool(row.get("importable", False) or not impl)
        critical = bool(impl)
        passed = bool((not critical or import_ok) and metadata_ok and trend_pass)
        rows.append(
            EquationReverseCheck(
                equation_id=equation_id,
                implementation_function=impl,
                check_type="registry_to_code_reverse",
                value=1.0 if passed else 0.0,
                unit="-",
                passed=passed,
                diagnostic="implementation, units, dimensional signature, benchmark and residual metadata are consistent" if passed else "missing implementation or registry metadata",
            )
        )
    return pd.DataFrame([item.as_dict() for item in rows])


def equation_reverse_check_summary() -> dict[str, Any]:
    """Return compact release-gate summary."""
    df = run_equation_reverse_checks()
    if df.empty:
        return {"passed": False, "rows": 0, "failed": 0}
    failed = int((~df["passed"].astype(bool)).sum())
    return {"passed": failed == 0, "rows": int(len(df)), "failed": failed}

