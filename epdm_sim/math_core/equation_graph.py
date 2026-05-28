"""Equation graph helpers for the V6.0 math core."""

from __future__ import annotations

import pandas as pd

from ..equation_residual_coupling import equation_residual_coupling_dataframe


def equation_graph_dataframe() -> pd.DataFrame:
    """Return graph-style edges from equation to implementation/residual/benchmark."""
    coupling = equation_residual_coupling_dataframe()
    rows = []
    for _, row in coupling.iterrows():
        equation_id = str(row.get("equation_id", ""))
        rows.extend(
            [
                {"source": equation_id, "target": row.get("implementation_function", ""), "edge_type": "implemented_by", "passed": bool(row.get("trend_check_passed", False))},
                {"source": equation_id, "target": row.get("residual_id", ""), "edge_type": "constrained_by_residual", "passed": bool(row.get("residual_coupled", False))},
                {"source": equation_id, "target": row.get("benchmark_id", ""), "edge_type": "validated_by_benchmark", "passed": bool(str(row.get("benchmark_id", "")))},
            ]
        )
    return pd.DataFrame(rows)


def equation_graph_acceptance() -> dict[str, int | bool]:
    """Return compact equation graph acceptance status."""
    df = equation_graph_dataframe()
    failed = int((~df["passed"].astype(bool)).sum()) if not df.empty else 1
    return {"passed": failed == 0, "edges": int(len(df)), "failed": failed}
