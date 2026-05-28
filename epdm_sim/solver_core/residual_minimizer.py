"""Residual minimization helpers with bounded corrections."""

from __future__ import annotations

from typing import Any

import pandas as pd

from ..residual_solver import (
    adjust_flash_split_to_close_mass,
    heat_balance_residual_correction,
    residual_acceptance_summary,
    solve_recycle_with_residual_minimization,
)


def enforce_phase_split_constraints(inlet_kg_h: float, vapor_kg_h: float, liquid_kg_h: float) -> dict[str, Any]:
    """Return bounded phase-split closure diagnostics."""
    return adjust_flash_split_to_close_mass(inlet_kg_h, vapor_kg_h, liquid_kg_h).as_dict()


def enforce_heat_balance_constraints(q_rxn_kW: float, q_reported_kW: float) -> dict[str, Any]:
    """Return bounded heat-balance closure diagnostics."""
    return heat_balance_residual_correction(q_rxn_kW, q_reported_kW).as_dict()


def residual_minimizer_dataframe(result_or_system: Any | None = None) -> pd.DataFrame:
    """Return representative residual-minimization checks."""
    rows = [
        solve_recycle_with_residual_minimization(100.0, 100.0).as_dict(),
        adjust_flash_split_to_close_mass(100.0, 10.0, 90.0).as_dict(),
        heat_balance_residual_correction(5.0, 5.0).as_dict(),
    ]
    if result_or_system is not None:
        rows.append({"correction_id": "residual_acceptance", **residual_acceptance_summary(result_or_system)})
    return pd.DataFrame(rows)
