"""Structured 2D meshes for lightweight CFD visualizations."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from pydantic import BaseModel, Field


class CFDGeometryConfig(BaseModel):
    """Geometry and mesh settings for the simplified CFD module."""

    geometry_type: str = "Reactor cross-section"
    nx: int = Field(default=80, ge=20, le=160)
    ny: int = Field(default=40, ge=10, le=100)
    pipe_length_m: float = 20.0
    pipe_diameter_m: float = 0.025
    reactor_diameter_m: float = 0.22
    liquid_height_m: float = 0.20
    impeller_diameter_m: float = 0.08
    annulus_inner_diameter_m: float = 0.16
    annulus_outer_diameter_m: float = 0.22


@dataclass
class StructuredMesh:
    """Structured CFD mesh with active-cell mask and wall distance."""

    x: np.ndarray
    y: np.ndarray
    X: np.ndarray
    Y: np.ndarray
    mask: np.ndarray
    wall_distance_m: np.ndarray
    dx: float
    dy: float
    length_scale_m: float
    geometry_type: str

    @property
    def shape(self) -> tuple[int, int]:
        """Return mesh shape."""
        return self.X.shape


def create_mesh(config: CFDGeometryConfig) -> StructuredMesh:
    """Create a structured 2D mesh for pipe, reactor section or annulus."""
    geometry = config.geometry_type
    if geometry == "Pipe 2D":
        x = np.linspace(0.0, max(config.pipe_length_m, 1.0e-6), config.nx)
        y = np.linspace(0.0, max(config.pipe_diameter_m, 1.0e-6), config.ny)
        X, Y = np.meshgrid(x, y, indexing="xy")
        mask = np.ones_like(X, dtype=bool)
        wall_distance = np.minimum(Y, config.pipe_diameter_m - Y)
        scale = config.pipe_diameter_m
    elif geometry == "Annulus":
        outer_r = max(config.annulus_outer_diameter_m / 2.0, 1.0e-6)
        inner_r = max(min(config.annulus_inner_diameter_m / 2.0, outer_r * 0.95), 1.0e-6)
        x = np.linspace(-outer_r, outer_r, config.nx)
        y = np.linspace(-outer_r, outer_r, config.ny)
        X, Y = np.meshgrid(x, y, indexing="xy")
        radius = np.sqrt(X**2 + Y**2)
        mask = (radius >= inner_r) & (radius <= outer_r)
        wall_distance = np.minimum(np.abs(radius - inner_r), np.abs(outer_r - radius))
        scale = outer_r - inner_r
    else:
        radius = max(config.reactor_diameter_m / 2.0, 1.0e-6)
        x = np.linspace(-radius, radius, config.nx)
        y = np.linspace(-radius, radius, config.ny)
        X, Y = np.meshgrid(x, y, indexing="xy")
        r = np.sqrt(X**2 + Y**2)
        mask = r <= radius
        wall_distance = np.maximum(radius - r, 0.0)
        scale = radius
        geometry = "Reactor cross-section"
    dx = float(abs(x[1] - x[0])) if len(x) > 1 else 1.0
    dy = float(abs(y[1] - y[0])) if len(y) > 1 else 1.0
    wall_distance = np.where(mask, np.maximum(wall_distance, 0.0), 0.0)
    return StructuredMesh(
        x=x,
        y=y,
        X=X,
        Y=Y,
        mask=mask,
        wall_distance_m=wall_distance,
        dx=dx,
        dy=dy,
        length_scale_m=max(scale, 1.0e-6),
        geometry_type=geometry,
    )
