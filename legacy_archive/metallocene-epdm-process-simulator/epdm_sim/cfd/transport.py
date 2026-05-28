"""Lightweight finite-volume-style transport utilities."""

from __future__ import annotations

import numpy as np

from .mesh import StructuredMesh


def smooth_active_field(mesh: StructuredMesh, field: np.ndarray, iterations: int = 50, relaxation: float = 0.25) -> np.ndarray:
    """Diffuse/smooth a scalar field on active mesh cells using neighbor averaging."""
    values = field.copy()
    mask = mesh.mask
    for _ in range(max(iterations, 0)):
        neighbors = (
            np.roll(values, 1, axis=0)
            + np.roll(values, -1, axis=0)
            + np.roll(values, 1, axis=1)
            + np.roll(values, -1, axis=1)
        ) / 4.0
        values = np.where(mask, (1.0 - relaxation) * values + relaxation * neighbors, np.nan)
        values = np.where(np.isnan(values), field, values)
    return values


def apply_pipe_inlet_outlet(field: np.ndarray, inlet_value: float, wall_value: float | None = None) -> np.ndarray:
    """Apply simple pipe inlet, outlet and optional wall scalar boundary conditions."""
    values = field.copy()
    values[:, 0] = inlet_value
    values[:, -1] = values[:, -2]
    if wall_value is not None:
        values[0, :] = wall_value
        values[-1, :] = wall_value
    return values


def normalized_active(mesh: StructuredMesh, values: np.ndarray) -> np.ndarray:
    """Normalize active field values to [0, 1]."""
    active = values[mesh.mask]
    if active.size == 0:
        return np.zeros_like(values)
    vmin = float(np.nanmin(active))
    vmax = float(np.nanmax(active))
    if abs(vmax - vmin) < 1.0e-12:
        return np.zeros_like(values)
    return np.where(mesh.mask, (values - vmin) / (vmax - vmin), 0.0)
