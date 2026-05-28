"""Conservation-constrained solve-path helpers for V6.2.

These helpers intentionally perform only small, auditable closure corrections.
Large residuals, polymer vapor leakage and heat-duty sign/unit problems remain
critical diagnostics instead of being hidden by numeric projection.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from ..residual_system import ResidualSystem, build_flowsheet_residual_system, make_residual, residual_system_acceptance
from .conservation_correction import (
    close_flash_split_residual,
    close_small_energy_residual,
    close_small_mass_residual,
    correction_certificate_dataframe,
    reject_large_residual_correction,
)


def _as_system(result_or_system: Any | None) -> ResidualSystem:
    """Return a residual system from a flowsheet result or an existing system."""
    if isinstance(result_or_system, ResidualSystem):
        return result_or_system
    if result_or_system is None:
        return ResidualSystem()
    return build_flowsheet_residual_system(result_or_system)


def apply_conservation_corrections_to_flowsheet(result_or_system: Any | None = None) -> dict[str, Any]:
    """Apply accepted small residual corrections and return a solve certificate."""
    system = _as_system(result_or_system)
    certificates = correction_certificate_dataframe(system)
    rejected = int(certificates["rejected"].astype(bool).sum()) if not certificates.empty and "rejected" in certificates else 0
    critical_sources = sorted(
        {
            str(row.get("suspected_source", ""))
            for _, row in certificates.iterrows()
            if bool(row.get("rejected", False)) or str(row.get("severity", "")).lower() == "critical"
        }
    )
    accepted_rows = certificates[~certificates.get("rejected", pd.Series(False, index=certificates.index)).astype(bool)] if not certificates.empty else pd.DataFrame()
    total_after = float(pd.to_numeric(accepted_rows.get("absolute_error_after", pd.Series(dtype=float)), errors="coerce").fillna(0.0).sum())
    status = residual_system_acceptance(system)
    return {
        "solve_path": "conservation_correction",
        "accepted": bool(rejected == 0 and status["passed"]),
        "correction_count": int(len(certificates)),
        "rejected_count": rejected,
        "absolute_error_after_sum": total_after,
        "residual_score": float(status["overall_score"]),
        "critical_sources": "; ".join(item for item in critical_sources if item),
        "solver_certificate_passed": bool(rejected == 0 and np.isfinite(total_after)),
    }


def solve_flash_with_mass_closure(
    inlet: float,
    vapor: float,
    liquid: float,
    *,
    polymer_vapor: float = 0.0,
    unit: str = "kg/h",
    tolerance: float = 1.0e-6,
    max_relative_pct: float = 0.10,
) -> dict[str, Any]:
    """Close a small flash split mismatch while keeping polymer vapor critical."""
    row = close_flash_split_residual(inlet, vapor, liquid, unit=unit, tolerance=tolerance, max_relative_pct=max_relative_pct)
    polymer_vapor_f = float(polymer_vapor)
    if polymer_vapor_f > float(tolerance):
        row.update(
            {
                "accepted": False,
                "severity": "critical",
                "rejected": True,
                "polymer_vapor": polymer_vapor_f,
                "suspected_source": "flash",
                "suggested_fix": "Polymer pseudo-component must remain in liquid; inspect flash split and component typing.",
            }
        )
    else:
        row["polymer_vapor"] = polymer_vapor_f
        row["rejected"] = reject_large_residual_correction(row)
    return row


def solve_heat_balance_with_energy_closure(
    heat_generated: float,
    heat_removed: float,
    *,
    unit: str = "kW",
    tolerance: float = 0.10,
    max_relative_pct: float = 0.50,
) -> dict[str, Any]:
    """Close a small heat-balance residual and reject sign/unit mistakes."""
    residual = make_residual(
        "heat_balance_solve",
        "heat generated ~= heat removed + accumulation",
        float(heat_generated),
        float(heat_removed),
        unit,
        float(tolerance),
        "heat_balance",
        "Check heat-duty sign convention and kJ/h to kW conversion before correction.",
        "error",
    )
    row = close_small_energy_residual(residual, max_relative_pct=max_relative_pct)
    row["solve_path"] = "heat_balance"
    row["rejected"] = reject_large_residual_correction(row)
    return row


def solve_recycle_with_residual_acceptance(
    inlet: float,
    outlet: float,
    *,
    unit: str = "kg/h",
    tolerance: float = 0.10,
    max_relative_pct: float = 0.10,
) -> dict[str, Any]:
    """Return an accepted/rejected recycle closure correction."""
    residual = make_residual(
        "recycle_closure_solve",
        "recycle inlet ~= recycle outlet",
        float(inlet),
        float(outlet),
        unit,
        float(tolerance),
        "recycle",
        "Inspect recycle iteration convergence and purge/recycle split.",
        "warning",
    )
    row = close_small_mass_residual(residual, max_relative_pct=max_relative_pct)
    row["solve_path"] = "recycle"
    row["rejected"] = reject_large_residual_correction(row)
    return row


def conservation_solve_certificate_dataframe(result_or_system: Any | None = None) -> pd.DataFrame:
    """Return V6.2 conservation solve-path certificate rows."""
    system = _as_system(result_or_system)
    rows: list[dict[str, Any]] = []
    corrections = correction_certificate_dataframe(system)
    if not corrections.empty:
        for _, row in corrections.iterrows():
            payload = row.to_dict()
            payload.setdefault("solve_path", "flowsheet_residual")
            payload["certificate_type"] = "residual_correction"
            rows.append(payload)
    rows.append({**solve_flash_with_mass_closure(100.0, 20.0, 80.0), "certificate_type": "flash_mass_closure"})
    rows.append({**solve_heat_balance_with_energy_closure(10.0, 10.0), "certificate_type": "heat_energy_closure"})
    rows.append({**solve_recycle_with_residual_acceptance(10.0, 10.0), "certificate_type": "recycle_closure"})
    summary = apply_conservation_corrections_to_flowsheet(system)
    rows.append({**summary, "correction_id": "conservation_solve_summary", "certificate_type": "summary", "severity": "ok" if summary["accepted"] else "critical", "rejected": not summary["accepted"]})
    return pd.DataFrame(rows)
