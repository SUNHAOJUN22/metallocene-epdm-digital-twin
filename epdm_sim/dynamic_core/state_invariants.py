"""Dynamic state invariant checks for V6.0."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def state_invariants_dataframe(dynamic_result: Any) -> pd.DataFrame:
    """Return monotonicity, positivity and quench invariant checks."""
    profile = getattr(dynamic_result, "profile", pd.DataFrame())
    if profile is None or profile.empty:
        return pd.DataFrame([{"invariant_id": "profile_present", "passed": False, "severity": "critical", "detail": "empty profile"}])
    rows = []
    if "polymer_mass_kg" in profile:
        rows.append({"invariant_id": "polymer_mass_nondecreasing", "passed": bool(profile["polymer_mass_kg"].diff().dropna().ge(-1.0e-10).all()), "severity": "error", "detail": "polymer mass accumulation"})
    for col in [c for c in profile.columns if c.startswith("segment_")]:
        rows.append({"invariant_id": f"{col}_nondecreasing", "passed": bool(profile[col].diff().dropna().ge(-1.0e-10).all()), "severity": "warning", "detail": "segment mass accumulation"})
    if "T_K" in profile:
        rows.append({"invariant_id": "temperature_finite_positive", "passed": bool(np.isfinite(profile["T_K"]).all() and (profile["T_K"] > 0).all()), "severity": "critical", "detail": "absolute temperature"})
    if "P_Pa" in profile:
        rows.append({"invariant_id": "pressure_finite_positive", "passed": bool(np.isfinite(profile["P_Pa"]).all() and (profile["P_Pa"] > 0).all()), "severity": "critical", "detail": "absolute pressure"})
    rate_cols = [col for col in profile.columns if col.startswith("r_")]
    if rate_cols:
        final_rate = float(profile[rate_cols].iloc[-1].abs().sum())
        rows.append({"invariant_id": "final_rate_bounded_after_quench", "passed": bool(np.isfinite(final_rate) and final_rate <= 1.0e6), "severity": "warning", "detail": f"final_rate={final_rate:.6g}"})
    return pd.DataFrame(rows)


def state_invariants_status(dynamic_result: Any) -> dict[str, int | bool]:
    """Return compact state invariant status."""
    df = state_invariants_dataframe(dynamic_result)
    hard = df[df["severity"].astype(str).isin(["error", "critical"])] if not df.empty else df
    failed = int((~hard["passed"].astype(bool)).sum()) if not hard.empty else 1
    return {"passed": bool(not df.empty and failed == 0), "rows": int(len(df)), "failed": failed}
