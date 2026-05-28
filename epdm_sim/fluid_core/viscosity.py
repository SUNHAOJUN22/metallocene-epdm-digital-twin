"""Viscosity helpers."""

from __future__ import annotations

from ..dimensioned import ensure_viscosity_Pa_s


def viscosity_Pa_s(value, *, default_unit: str = "Pa.s") -> float:
    """Return viscosity in Pa.s."""
    return ensure_viscosity_Pa_s(value, default_unit=default_unit)

