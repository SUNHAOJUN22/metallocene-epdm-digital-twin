"""Integrate V6.4 residual-loop diagnostics into solve-path certificates."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from ..residual_system import ResidualSystem, build_flowsheet_residual_system
from .conservation_solve_path import conservation_solve_certificate_dataframe
from .equation_oriented_solver import equation_oriented_solver_certificate
from .nonlinear_residual_loop import nonlinear_residual_iteration, residual_iteration_certificate


def _as_system(result_or_system: Any | None) -> ResidualSystem:
    if isinstance(result_or_system, ResidualSystem):
        return result_or_system
    if result_or_system is None:
        return ResidualSystem()
    return build_flowsheet_residual_system(result_or_system)


def solve_recycle_flash_heat_loop(result_or_system: Any | None = None) -> dict[str, Any]:
    """Return a combined solve-path status for recycle, flash and heat closure."""
    system = _as_system(result_or_system)
    nonlinear = nonlinear_residual_iteration(system)
    conservation = conservation_solve_certificate_dataframe(system)
    equation = equation_oriented_solver_certificate(system)
    rejected = bool(
        nonlinear.get("rejected", pd.Series(False, index=nonlinear.index)).astype(bool).any()
        or conservation.get("rejected", pd.Series(False, index=conservation.index)).astype(bool).any()
        or (~equation.get("passed", pd.Series(True, index=equation.index)).astype(bool)).any()
    )
    max_norm = float(pd.to_numeric(nonlinear.get("residual_norm_after", pd.Series([0.0])), errors="coerce").fillna(0.0).max())
    return {
        "solve_path": "recycle_flash_heat_loop",
        "accepted": not rejected,
        "rejected": rejected,
        "residual_norm_after": max_norm,
        "iteration_count": int(len(nonlinear)),
        "conservation_rows": int(len(conservation)),
        "equation_rows": int(len(equation)),
        "finite": bool(np.isfinite(max_norm)),
        "rejected_reason": "" if not rejected else "one or more residual solve-path certificates rejected",
    }


def solve_path_integrator_dataframe(result_or_system: Any | None = None) -> pd.DataFrame:
    """Return V6.4 solve-path integrator rows."""
    system = _as_system(result_or_system)
    summary = solve_recycle_flash_heat_loop(system)
    rows: list[dict[str, Any]] = []
    for path, frame in [
        ("nonlinear_residual_loop", residual_iteration_certificate(system)),
        ("conservation_solve_path", conservation_solve_certificate_dataframe(system)),
        ("equation_oriented_solver", equation_oriented_solver_certificate(system)),
    ]:
        rows.append(
            {
                "solve_path": path,
                "rows": int(len(frame)),
                "accepted": bool(not frame.empty and not frame.get("rejected", pd.Series(False, index=frame.index)).fillna(False).astype(bool).any()),
                "rejected": bool(frame.empty or frame.get("rejected", pd.Series(False, index=frame.index)).fillna(False).astype(bool).any()),
                "residual_norm_after": float(pd.to_numeric(frame.get("residual_norm_after", pd.Series([0.0])), errors="coerce").fillna(0.0).max()),
                "rejected_reason": "",
            }
        )
    rows.append({**summary, "rows": int(sum(row["rows"] for row in rows))})
    return pd.DataFrame(rows)


def solve_path_integrator_gate(result_or_system: Any | None = None) -> dict[str, Any]:
    """Return compact gate status for solve-path integration."""
    df = solve_path_integrator_dataframe(result_or_system)
    rejected = int(df["rejected"].astype(bool).sum()) if not df.empty and "rejected" in df else 1
    finite = bool(np.isfinite(pd.to_numeric(df.get("residual_norm_after", pd.Series([0.0])), errors="coerce").fillna(0.0)).all())
    return {"passed": bool(rejected == 0 and finite), "rows": int(len(df)), "rejected": rejected, "finite": finite}

