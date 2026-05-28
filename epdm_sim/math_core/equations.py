"""Equation-level math-kernel summaries.

These helpers intentionally wrap the existing equation registry/binding layer
instead of replacing it.  They give V5.7 a stable math-core namespace while
keeping the older public APIs compatible.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from ..equation_binding import equation_binding_dataframe, run_equation_binding_checks
from ..equation_reverse_check import run_equation_reverse_checks


def equation_kernel_dataframe() -> pd.DataFrame:
    """Return equation binding rows with reverse-check status."""
    bindings = equation_binding_dataframe()
    reverse = run_equation_reverse_checks()[["equation_id", "passed", "diagnostic"]].rename(
        columns={"passed": "reverse_check_passed", "diagnostic": "reverse_diagnostic"}
    )
    if bindings.empty:
        return pd.DataFrame()
    return bindings.merge(reverse, on="equation_id", how="left")


def equation_kernel_acceptance() -> dict[str, Any]:
    """Return release-gate style equation acceptance summary."""
    checks = run_equation_binding_checks()
    reverse = run_equation_reverse_checks()
    binding_failures = int((~checks["passed"].astype(bool)).sum()) if not checks.empty else 1
    reverse_failures = int((~reverse["passed"].astype(bool)).sum()) if not reverse.empty else 1
    return {
        "passed": binding_failures == 0 and reverse_failures == 0,
        "binding_failures": binding_failures,
        "reverse_failures": reverse_failures,
        "equation_count": int(len(checks)),
    }

