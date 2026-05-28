"""Heat-capacity helpers."""

from __future__ import annotations


def mixture_heat_capacity_kJ_kgK(solvent_cp: float, polymer_cp: float, solids_wt: float) -> float:
    """Return positive mass-weighted mixture heat capacity."""
    frac = max(min(float(solids_wt) / 100.0, 1.0), 0.0)
    return max((1.0 - frac) * float(solvent_cp) + frac * float(polymer_cp), 1.0e-12)

