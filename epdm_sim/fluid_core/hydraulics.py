"""Hydraulic trend helpers."""

from __future__ import annotations

from ..transport_core import pressure_drop_laminar_kPa


def darcy_pressure_drop_kPa(flow_kg_h: float, density_kg_m3: float, viscosity_Pa_s: float, diameter_m: float, length_m: float) -> float:
    """Return Darcy-Weisbach pressure drop in kPa."""
    flow_m3_h = max(float(flow_kg_h), 0.0) / max(float(density_kg_m3), 1.0e-12)
    return pressure_drop_laminar_kPa(flow_m3_h, viscosity_Pa_s, length_m, diameter_m)
