"""Small-balance correction certificates for V6.1 conservation gates."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from ..residual_system import Residual, ResidualSystem, build_flowsheet_residual_system


def close_small_mass_residual(residual: Residual, *, max_relative_pct: float = 0.10) -> dict[str, Any]:
    """Close a small mass residual without hiding large conservation errors."""
    rel = float(abs(residual.relative_error_pct))
    allowed = bool(residual.severity != "critical" and rel <= float(max_relative_pct) and np.isfinite(residual.absolute_error))
    corrected_rhs = float(residual.lhs) if allowed else float(residual.rhs)
    return {
        "correction_id": f"{residual.residual_id}_mass_correction",
        "residual_id": residual.residual_id,
        "before_lhs": float(residual.lhs),
        "before_rhs": float(residual.rhs),
        "after_rhs": corrected_rhs,
        "absolute_error_before": float(residual.absolute_error),
        "absolute_error_after": 0.0 if allowed else float(residual.absolute_error),
        "relative_error_pct": rel,
        "unit": residual.unit,
        "tolerance": float(residual.tolerance),
        "accepted": allowed,
        "severity": "ok" if allowed else "critical",
        "suspected_source": residual.suspected_source or "mass_balance",
        "suggested_fix": "" if allowed else residual.suggested_fix or "Do not correct large mass residuals; inspect the source unit operation.",
    }


def close_small_energy_residual(residual: Residual, *, max_relative_pct: float = 0.50) -> dict[str, Any]:
    """Close a small energy residual while rejecting sign/unit mistakes."""
    rel = float(abs(residual.relative_error_pct))
    same_sign = float(residual.lhs) == 0.0 or float(residual.rhs) == 0.0 or np.sign(residual.lhs) == np.sign(residual.rhs)
    allowed = bool(residual.severity != "critical" and same_sign and rel <= float(max_relative_pct) and np.isfinite(residual.absolute_error))
    corrected_rhs = float(residual.lhs) if allowed else float(residual.rhs)
    return {
        "correction_id": f"{residual.residual_id}_energy_correction",
        "residual_id": residual.residual_id,
        "before_lhs": float(residual.lhs),
        "before_rhs": float(residual.rhs),
        "after_rhs": corrected_rhs,
        "absolute_error_before": float(residual.absolute_error),
        "absolute_error_after": 0.0 if allowed else float(residual.absolute_error),
        "relative_error_pct": rel,
        "unit": residual.unit,
        "tolerance": float(residual.tolerance),
        "accepted": allowed,
        "severity": "ok" if allowed else "critical",
        "suspected_source": residual.suspected_source or "heat_balance",
        "suggested_fix": "" if allowed else residual.suggested_fix or "Check heat-duty sign and kJ/h to kW conversion before correction.",
    }


def close_flash_split_residual(
    inlet: float,
    vapor: float,
    liquid: float,
    *,
    unit: str = "kg/h",
    tolerance: float = 1.0e-6,
    max_relative_pct: float = 0.10,
) -> dict[str, Any]:
    """Adjust a tiny flash liquid split mismatch and reject large mismatch."""
    inlet_f = float(inlet)
    vapor_f = max(float(vapor), 0.0)
    liquid_f = max(float(liquid), 0.0)
    rhs = vapor_f + liquid_f
    abs_err = abs(inlet_f - rhs)
    rel = 100.0 * abs_err / max(abs(inlet_f), abs(rhs), 1.0e-12)
    allowed = bool(abs_err <= float(tolerance) or rel <= float(max_relative_pct))
    corrected_liquid = max(inlet_f - vapor_f, 0.0) if allowed else liquid_f
    return {
        "correction_id": "flash_split_correction",
        "residual_id": "flash_phase_mass",
        "before_lhs": inlet_f,
        "before_rhs": rhs,
        "after_rhs": vapor_f + corrected_liquid,
        "vapor": vapor_f,
        "liquid_before": liquid_f,
        "liquid_after": corrected_liquid,
        "absolute_error_before": abs_err,
        "absolute_error_after": abs(inlet_f - vapor_f - corrected_liquid),
        "relative_error_pct": rel,
        "unit": unit,
        "tolerance": float(tolerance),
        "accepted": allowed,
        "severity": "ok" if allowed else "critical",
        "suspected_source": "flash",
        "suggested_fix": "" if allowed else "Re-run flash split; do not hide a large vapor/liquid mass mismatch.",
    }


def reject_large_residual_correction(correction: dict[str, Any], *, max_relative_pct: float = 1.0) -> bool:
    """Return whether a correction must be rejected as physically unsafe."""
    if str(correction.get("severity", "")).lower() == "critical":
        return True
    if not bool(correction.get("accepted", False)):
        return True
    return float(correction.get("relative_error_pct", 0.0) or 0.0) > float(max_relative_pct)


def correction_certificate_dataframe(result_or_system: Any | None = None) -> pd.DataFrame:
    """Return correction certificates for mass and energy residuals."""
    if isinstance(result_or_system, ResidualSystem):
        system = result_or_system
    elif result_or_system is None:
        system = ResidualSystem()
    else:
        system = build_flowsheet_residual_system(result_or_system)
    rows: list[dict[str, Any]] = []
    for residual in system.mass_residuals + system.phase_residuals + system.reaction_residuals:
        rows.append(close_small_mass_residual(residual))
    for residual in system.energy_residuals:
        rows.append(close_small_energy_residual(residual))
    if not rows:
        rows.append({"correction_id": "not_run", "accepted": True, "severity": "ok", "suggested_fix": "No residual system supplied."})
    df = pd.DataFrame(rows)
    df["rejected"] = df.apply(lambda row: reject_large_residual_correction(row.to_dict()), axis=1)
    return df
