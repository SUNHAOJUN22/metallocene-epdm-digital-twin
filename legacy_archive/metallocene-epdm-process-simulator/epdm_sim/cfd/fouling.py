"""Fouling-risk field calculations for EPDM CFD visualizations."""

from __future__ import annotations

import numpy as np

from .mesh import StructuredMesh


def calculate_fouling_field(
    mesh: StructuredMesh,
    speed: np.ndarray,
    temperature_C: np.ndarray,
    solids_wt: np.ndarray,
    viscosity_Pa_s: np.ndarray,
    base_viscosity_Pa_s: float,
    solids_ref_wt: float = 12.0,
    temperature_ref_C: float = 100.0,
) -> np.ndarray:
    """Calculate local wall/dead-zone/polymer fouling risk index."""
    mean_speed = max(float(np.nanmean(speed[mesh.mask])), 1.0e-6)
    wall_factor = np.exp(-mesh.wall_distance_m / max(0.12 * mesh.length_scale_m, 1.0e-6))
    low_velocity_factor = np.clip(mean_speed / (speed + 0.05 * mean_speed), 0.0, 12.0)
    high_polymer_factor = np.clip(solids_wt / max(solids_ref_wt, 1.0e-6), 0.0, 5.0)
    high_temperature_factor = np.exp(np.clip((temperature_C - temperature_ref_C) / 20.0, -3.0, 3.0))
    normalized_viscosity = np.clip(viscosity_Pa_s / max(base_viscosity_Pa_s, 1.0e-8), 0.05, 30.0)
    risk = normalized_viscosity * wall_factor * low_velocity_factor * high_polymer_factor * high_temperature_factor
    return np.where(mesh.mask, risk, np.nan)


def risk_level(max_risk: float) -> str:
    """Return qualitative fouling-risk class."""
    if max_risk <= 1.0:
        return "low"
    if max_risk <= 3.0:
        return "medium"
    return "high"
