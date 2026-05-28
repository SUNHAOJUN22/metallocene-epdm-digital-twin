"""Density helpers."""

from __future__ import annotations

from ..dimensioned import ensure_density_kg_m3


def density_kg_m3(value, *, default_unit: str = "kg/m3") -> float:
    """Return density in kg/m3."""
    return ensure_density_kg_m3(value, default_unit=default_unit)

