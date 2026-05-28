"""Residual graph and suspected-source traceability for V6.0."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .residual_system import ResidualSystem, build_flowsheet_residual_system


def build_residual_graph(result_or_system: Any) -> pd.DataFrame:
    """Return residual -> suspected source/fix graph rows."""
    system = result_or_system if isinstance(result_or_system, ResidualSystem) else build_flowsheet_residual_system(result_or_system)
    rows = []
    for residual in system.all_residuals():
        rows.append(
            {
                "residual_id": residual.residual_id,
                "equation": residual.equation,
                "suspected_source": residual.suspected_source or "accepted",
                "suggested_fix": residual.suggested_fix,
                "severity": residual.severity,
                "passed": residual.passed,
            }
        )
    return pd.DataFrame(rows)


def residual_traceability_summary(result_or_system: Any) -> dict[str, int | bool]:
    """Return compact residual graph status."""
    df = build_residual_graph(result_or_system)
    hard = df[df["severity"].astype(str).isin(["error", "critical"])] if not df.empty else df
    failed = int((~hard["passed"].astype(bool)).sum()) if not hard.empty else 0
    return {"passed": bool(not df.empty and failed == 0), "rows": int(len(df)), "failed_hard": failed}
