"""Reusable ODE event helpers for template dynamic reactors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ODEEventRecord:
    """One dynamic-reactor event entry."""

    time_min: float
    event_id: str
    message: str
    severity: str = "info"

    def as_dict(self) -> dict[str, Any]:
        return {
            "time_min": self.time_min,
            "event_id": self.event_id,
            "message": self.message,
            "severity": self.severity,
        }


def quench_event(time_min: float, quench_time_min: float) -> float:
    """Event function crossing zero at quench time."""
    return time_min - quench_time_min


def runaway_event(temperature_K: float, high_alarm_K: float) -> float:
    """Event function crossing zero at high-temperature alarm."""
    return temperature_K - high_alarm_K


def feed_cutoff_event(pressure_Pa: float, setpoint_Pa: float) -> float:
    """Event function crossing zero when pressure reaches the feed cutoff."""
    return pressure_Pa - setpoint_Pa


def end_reaction_event(time_min: float, end_time_min: float) -> float:
    """Event function crossing zero at recipe end."""
    return time_min - end_time_min


def event_log_dataframe(events: list[ODEEventRecord]):
    """Return event records as a DataFrame."""
    import pandas as pd

    return pd.DataFrame([event.as_dict() for event in events])

