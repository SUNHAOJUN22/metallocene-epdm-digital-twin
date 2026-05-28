"""DAE-style dynamic constraints for V6.0 state diagnostics."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def dae_constraints_dataframe(dynamic_result: Any) -> pd.DataFrame:
    """Return DAE/state algebraic constraint checks for a dynamic profile."""
    profile = getattr(dynamic_result, "profile", pd.DataFrame())
    if profile is None or profile.empty:
        return pd.DataFrame([{"constraint_id": "profile_present", "passed": False, "severity": "critical", "value": np.nan, "unit": "-"}])
    rows = []
    checks = {
        "liquid_moles_nonnegative": [col for col in profile.columns if col.startswith("n_liq_")],
        "gas_moles_nonnegative": [col for col in profile.columns if col.startswith("n_gas_")],
        "segment_mass_nonnegative": [col for col in profile.columns if col.startswith("segment_")],
    }
    for cid, cols in checks.items():
        if cols:
            value = float(profile[cols].min().min())
            rows.append({"constraint_id": cid, "passed": value >= -1.0e-12, "severity": "error", "value": value, "unit": "state"})
    for cid, col, threshold in [
        ("polymer_mass_nonnegative", "polymer_mass_kg", 0.0),
        ("temperature_positive", "T_K", 0.0),
        ("pressure_positive", "P_Pa", 0.0),
        ("catalyst_active_nonnegative", "catalyst_active_mol", 0.0),
    ]:
        if col in profile:
            value = float(profile[col].min())
            rows.append({"constraint_id": cid, "passed": value >= threshold, "severity": "critical" if "positive" in cid else "error", "value": value, "unit": col})
    return pd.DataFrame(rows or [{"constraint_id": "constraints_detected", "passed": True, "severity": "ok", "value": 1.0, "unit": "-"}])


def dae_constraints_status(dynamic_result: Any) -> dict[str, int | bool]:
    """Return compact DAE constraints status."""
    df = dae_constraints_dataframe(dynamic_result)
    hard = df[df["severity"].astype(str).isin(["error", "critical"])]
    failed = int((~hard["passed"].astype(bool)).sum()) if not hard.empty else 0
    return {"passed": bool(not df.empty and failed == 0), "rows": int(len(df)), "failed": failed}
