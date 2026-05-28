"""Boundary-condition objects for lightweight CFD and OpenFOAM export."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BoundaryCondition:
    """Simple CFD boundary-condition descriptor."""

    name: str
    kind: str
    value: Any = None
    field: str = ""


def default_pipe_boundaries(inlet_velocity_m_s: float, wall_temperature_C: float, outlet_pressure_Pa: float) -> list[BoundaryCondition]:
    """Return consistent pipe BC names for the FVM and OpenFOAM skeleton."""
    return [
        BoundaryCondition("inlet", "fixedValue", (inlet_velocity_m_s, 0.0, 0.0), "U"),
        BoundaryCondition("outlet", "fixedValue", outlet_pressure_Pa, "p"),
        BoundaryCondition("walls", "noSlip", (0.0, 0.0, 0.0), "U"),
        BoundaryCondition("walls", "fixedValue", wall_temperature_C + 273.15, "T"),
        BoundaryCondition("frontAndBack", "empty", None, ""),
    ]
