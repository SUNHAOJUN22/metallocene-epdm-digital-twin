"""Dynamic event certificate helpers."""

from __future__ import annotations

from typing import Any

import pandas as pd


def event_certificate(event_id: str, triggered: bool, *, severity: str = "warning", reason: str = "") -> dict[str, Any]:
    """Return an event certificate row."""
    return {"event_id": event_id, "triggered": bool(triggered), "severity": severity if triggered else "ok", "reason": reason, "passed": not (triggered and severity == "critical")}


def event_certificate_dataframe(events: list[dict[str, Any]] | None = None) -> pd.DataFrame:
    """Return event certificates for dynamic profile governance."""
    events = events or [event_certificate("runaway", False), event_certificate("cooling_failure", False)]
    return pd.DataFrame(events)
