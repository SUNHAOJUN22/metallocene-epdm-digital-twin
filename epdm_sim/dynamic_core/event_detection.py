"""Dynamic event detection helpers for V6.3."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def detect_dynamic_events(dynamic_result: Any | None = None, *, high_temperature_K: float = 450.0) -> list[dict[str, Any]]:
    """Detect quench, cooling-failure and runaway-style events from a profile."""
    if dynamic_result is None:
        return [{"event": "none", "severity": "ok", "time_min": 0.0, "passed": True}]
    profile = getattr(dynamic_result, "profile", pd.DataFrame())
    summary = getattr(dynamic_result, "summary", {}) or {}
    rows: list[dict[str, Any]] = []
    if profile.empty:
        return [{"event": "missing_profile", "severity": "warning", "time_min": 0.0, "passed": False}]
    if "event" in profile and profile["event"].astype(str).str.contains("quench", case=False, na=False).any():
        t = float(profile.loc[profile["event"].astype(str).str.contains("quench", case=False, na=False), "time_min"].iloc[0])
        rows.append({"event": "quench", "severity": "ok", "time_min": t, "passed": True})
    if "T_K" in profile and float(profile["T_K"].max()) >= float(high_temperature_K):
        idx = profile["T_K"].idxmax()
        rows.append({"event": "runaway_temperature", "severity": "high", "time_min": float(profile.loc[idx, "time_min"]), "passed": False})
    if any("cooling" in str(w).lower() and "failure" in str(w).lower() for w in getattr(dynamic_result, "warnings", [])) or summary.get("cooling_failure"):
        rows.append({"event": "cooling_failure", "severity": "high", "time_min": float(profile["time_min"].iloc[-1]), "passed": False})
    if not rows:
        rows.append({"event": "none", "severity": "ok", "time_min": float(profile["time_min"].iloc[-1]) if "time_min" in profile else 0.0, "passed": True})
    for row in rows:
        row["finite"] = bool(np.isfinite(float(row["time_min"])))
    return rows


def dynamic_event_detection_dataframe(dynamic_result: Any | None = None) -> pd.DataFrame:
    """Return dynamic event detection rows."""
    return pd.DataFrame(detect_dynamic_events(dynamic_result))


def event_flags_summary(dynamic_result: Any | None = None) -> dict[str, Any]:
    """Return compact event flags for solver policy."""
    df = dynamic_event_detection_dataframe(dynamic_result)
    high = int(df["severity"].astype(str).str.lower().isin(["high", "critical"]).sum()) if not df.empty else 0
    return {"passed": high == 0, "event_count": int(len(df)), "high_risk_events": high, "event_flags": "; ".join(df.get("event", pd.Series(dtype=str)).astype(str))}

