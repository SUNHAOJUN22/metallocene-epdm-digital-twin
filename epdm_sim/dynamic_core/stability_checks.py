"""Proof-style dynamic stability checks for template ODE profiles."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .residual_feedback import residual_feedback_solver_status


def dynamic_stability_checks_dataframe(dynamic_result: Any) -> pd.DataFrame:
    """Return finite, monotonic and residual-feedback stability checks."""
    profile = getattr(dynamic_result, "profile", pd.DataFrame())
    summary = dict(getattr(dynamic_result, "summary", {}) or {})
    rows: list[dict[str, Any]] = []
    if profile.empty:
        return pd.DataFrame([{"check_id": "profile_present", "passed": False, "severity": "critical", "detail": "dynamic profile is empty"}])
    numeric = profile.select_dtypes(include="number")
    rows.append({"check_id": "numeric_finite", "passed": bool(np.isfinite(numeric.to_numpy()).all()), "severity": "error", "detail": "all numeric states finite"})
    for column in [col for col in ["polymer_mass_kg", "T_K", "P_Pa"] if col in profile.columns]:
        rows.append({"check_id": f"{column}_nonnegative", "passed": bool((profile[column] >= 0.0).all()), "severity": "error", "detail": column})
    if "polymer_mass_kg" in profile.columns:
        rows.append({"check_id": "polymer_mass_nondecreasing", "passed": bool(profile["polymer_mass_kg"].diff().dropna().ge(-1.0e-10).all()), "severity": "error", "detail": "polymer mass accumulation"})
    segment_cols = [col for col in profile.columns if col.startswith("segment_")]
    for col in segment_cols:
        rows.append({"check_id": f"{col}_nondecreasing", "passed": bool(profile[col].diff().dropna().ge(-1.0e-10).all()), "severity": "warning", "detail": "segment accumulation"})
    if "T_K" in profile.columns:
        rows.append({"check_id": "temperature_positive", "passed": bool((profile["T_K"] > 0.0).all()), "severity": "critical", "detail": "absolute temperature"})
    if "P_Pa" in profile.columns:
        rows.append({"check_id": "pressure_positive", "passed": bool((profile["P_Pa"] > 0.0).all()), "severity": "critical", "detail": "absolute pressure"})
    rate_cols = [col for col in profile.columns if col.startswith("r_")]
    if rate_cols:
        final_rate = float(profile.iloc[-1][rate_cols].abs().sum())
        rows.append({"check_id": "final_reaction_rate_bounded", "passed": final_rate <= 1.0e6, "severity": "warning", "detail": f"final_rate_sum={final_rate:.6g}"})
    feedback = residual_feedback_solver_status(dynamic_result)
    rows.append({"check_id": "residual_feedback_passed", "passed": bool(feedback["passed"]), "severity": "error", "detail": str(feedback)})
    rows.append({"check_id": "stiffness_indicator_finite", "passed": np.isfinite(float(summary.get("stiffness_indicator", 0.0) or 0.0)), "severity": "warning", "detail": "stiffness indicator finite or absent"})
    return pd.DataFrame(rows)


def dynamic_stability_status(dynamic_result: Any) -> dict[str, Any]:
    """Return compact stability status for release gates."""
    df = dynamic_stability_checks_dataframe(dynamic_result)
    if df.empty:
        return {"passed": False, "rows": 0, "failed": 0}
    hard = df[df["severity"].isin(["error", "critical"])]
    failed = int((~hard["passed"].astype(bool)).sum())
    return {"passed": failed == 0, "rows": int(len(df)), "failed": failed}


def stiffness_indicator_from_profile(dynamic_result: Any) -> float:
    """Return a lightweight stiffness indicator from T/P gradients."""
    profile = getattr(dynamic_result, "profile", pd.DataFrame())
    if profile.empty:
        return float("inf")
    gradients = []
    for col in ["T_K", "P_Pa", "polymer_mass_kg"]:
        if col in profile:
            gradients.append(float(profile[col].diff().abs().fillna(0.0).max()))
    return float(max(gradients) if gradients else 0.0)

