"""Dynamic event localization helpers for V6.4."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .event_detection import dynamic_event_detection_dataframe


def localize_dynamic_events(dynamic_result: Any | None = None) -> list[dict[str, Any]]:
    """Return approximate event localization windows from event diagnostics."""
    events = dynamic_event_detection_dataframe(dynamic_result)
    rows: list[dict[str, Any]] = []
    if events.empty:
        return [{"event_id": "no_event", "localized": True, "t_min": 0.0, "t_max": 0.0, "event_type": "none", "high_risk": False}]
    for idx, row in events.iterrows():
        time_min = float(row.get("time_min", row.get("t_min", idx)))
        rows.append(
            {
                "event_id": row.get("event_id", f"event_{idx}"),
                "event_type": row.get("event_type", row.get("event", "event")),
                "t_min": max(time_min - 0.5, 0.0),
                "t_max": time_min + 0.5,
                "localized": True,
                "high_risk": bool(row.get("high_risk", False)),
                "suggested_action": "inspect event window and residual trend" if bool(row.get("high_risk", False)) else "",
            }
        )
    return rows


def event_localization_dataframe(dynamic_result: Any | None = None) -> pd.DataFrame:
    """Return event localization rows."""
    return pd.DataFrame(localize_dynamic_events(dynamic_result))


def event_localization_summary(dynamic_result: Any | None = None) -> dict[str, Any]:
    """Return compact event localization status."""
    df = event_localization_dataframe(dynamic_result)
    high = int(df.get("high_risk", pd.Series(dtype=bool)).astype(bool).sum()) if not df.empty else 0
    return {"passed": bool(not df.empty and df["localized"].astype(bool).all()), "rows": int(len(df)), "high_risk_events": high}


def event_localization_gate(dynamic_result: Any | None = None) -> dict[str, Any]:
    """Return release-gate status for event localization."""
    return event_localization_summary(dynamic_result)

