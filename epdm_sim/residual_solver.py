"""Residual-driven closure helpers for V5.5.

These helpers do not replace first-principles balances.  They provide small,
auditable numerical closure corrections and hard rejection for large
mass/energy inconsistencies so downstream DOE, posterior and optimization
logic cannot silently accept nonphysical candidates.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd

from .residual_objective import residual_objective_score
from .residual_system import ResidualSystem, build_flowsheet_residual_system, critical_residuals
from .utils import safe_divide


@dataclass(frozen=True)
class ResidualCorrection:
    """One bounded residual correction proposal."""

    correction_id: str
    target: str
    before: float
    after: float
    correction: float
    unit: str
    relative_correction_pct: float
    severity: str
    accepted: bool
    suspected_source: str
    suggested_fix: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _system_from_result(result_or_system: Any) -> ResidualSystem:
    if isinstance(result_or_system, ResidualSystem):
        return result_or_system
    embedded = getattr(result_or_system, "residual_system", None)
    if isinstance(embedded, ResidualSystem):
        return embedded
    return build_flowsheet_residual_system(result_or_system)


def residual_weighted_objective(residual_system: ResidualSystem, *, critical_weight: float = 1000.0) -> float:
    """Return a residual objective that strongly penalizes critical failures."""
    critical_count = len(critical_residuals(residual_system))
    base = max(0.0, 100.0 - float(residual_system.overall_score))
    return base + max(float(critical_weight), 0.0) * critical_count


def solve_recycle_with_residual_minimization(
    tear_in_kg_h: float,
    tear_out_kg_h: float,
    *,
    tolerance_kg_h: float = 1.0e-3,
    max_relative_correction_pct: float = 2.0,
) -> ResidualCorrection:
    """Return a bounded recycle tear correction proposal.

    The after value is the corrected outlet flow.  Corrections larger than the
    configured relative threshold are rejected and flagged as errors.
    """
    before = float(tear_out_kg_h)
    target = float(tear_in_kg_h)
    correction = target - before
    rel = abs(100.0 * safe_divide(correction, max(abs(target), abs(before), 1.0), 0.0))
    accepted = abs(correction) <= tolerance_kg_h or rel <= max_relative_correction_pct
    severity = "ok" if accepted else "error"
    return ResidualCorrection(
        "recycle_tear_closure",
        "recycle_out_kg_h",
        before,
        target if accepted else before,
        correction if accepted else 0.0,
        "kg/h",
        rel,
        severity,
        accepted,
        "" if accepted else "recycle",
        "" if accepted else "Recycle tear mismatch exceeds safe correction threshold; inspect purge/recycle split.",
    )


def adjust_flash_split_to_close_mass(
    inlet_kg_h: float,
    vapor_kg_h: float,
    liquid_kg_h: float,
    *,
    max_relative_correction_pct: float = 0.5,
) -> ResidualCorrection:
    """Return a small flash liquid correction to close total mass.

    The correction is applied to the liquid stream because polymer and heavy
    liquid inventory are the safest bookkeeping location for small numerical
    closure errors.  Large errors are rejected.
    """
    inlet = float(inlet_kg_h)
    outlet = float(vapor_kg_h) + float(liquid_kg_h)
    correction = inlet - outlet
    rel = abs(100.0 * safe_divide(correction, max(abs(inlet), 1.0), 0.0))
    accepted = rel <= max_relative_correction_pct
    severity = "ok" if accepted else "critical"
    return ResidualCorrection(
        "flash_total_mass_closure",
        "liquid_kg_h",
        float(liquid_kg_h),
        float(liquid_kg_h) + correction if accepted else float(liquid_kg_h),
        correction if accepted else 0.0,
        "kg/h",
        rel,
        severity,
        accepted,
        "" if accepted else "flash",
        "" if accepted else "Flash mass mismatch is too large for numerical correction; inspect K values and split table.",
    )


def heat_balance_residual_correction(
    q_rxn_kW: float,
    q_reported_kW: float,
    *,
    max_relative_correction_pct: float = 1.0,
) -> ResidualCorrection:
    """Return a bounded heat-balance reporting correction."""
    target = float(q_rxn_kW)
    before = float(q_reported_kW)
    correction = target - before
    rel = abs(100.0 * safe_divide(correction, max(abs(target), abs(before), 1.0), 0.0))
    accepted = rel <= max_relative_correction_pct
    severity = "ok" if accepted else "critical"
    return ResidualCorrection(
        "heat_balance_closure",
        "reported_heat_kW",
        before,
        target if accepted else before,
        correction if accepted else 0.0,
        "kW",
        rel,
        severity,
        accepted,
        "" if accepted else "heat_balance",
        "" if accepted else "Heat residual exceeds correction threshold; check deltaH sign and kJ/h to kW conversion.",
    )


def residual_acceptance_summary(result_or_system: Any, *, minimum_score: float = 70.0) -> dict[str, Any]:
    """Return an audit-ready residual acceptance summary."""
    system = _system_from_result(result_or_system)
    critical = critical_residuals(system)
    objective = residual_weighted_objective(system)
    return {
        "passed": bool(not critical and system.overall_score >= minimum_score),
        "overall_score": float(system.overall_score),
        "minimum_score": float(minimum_score),
        "critical_count": len(critical),
        "residual_weighted_objective": objective,
        "residual_objective_score": residual_objective_score(system),
        "critical_sources": "; ".join(sorted({item.suspected_source for item in critical if item.suspected_source})),
    }


def residual_correction_trace_dataframe(corrections: list[ResidualCorrection] | None = None) -> pd.DataFrame:
    """Return correction proposals as a report table."""
    if corrections is None:
        corrections = [
            solve_recycle_with_residual_minimization(100.0, 100.0),
            adjust_flash_split_to_close_mass(100.0, 10.0, 90.0),
            heat_balance_residual_correction(5.0, 5.0),
        ]
    return pd.DataFrame([item.as_dict() for item in corrections])


def residual_solver_dataframe(result_or_system: Any | None = None) -> pd.DataFrame:
    """Return a compact residual-solver gate table."""
    if result_or_system is None:
        summary = {
            "passed": True,
            "overall_score": 100.0,
            "minimum_score": 70.0,
            "critical_count": 0,
            "residual_weighted_objective": 0.0,
            "residual_objective_score": 0.0,
            "critical_sources": "",
        }
    else:
        summary = residual_acceptance_summary(result_or_system)
    summary["gate"] = "residual_solver"
    return pd.DataFrame([summary])
