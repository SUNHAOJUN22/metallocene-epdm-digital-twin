"""Recycle closure helper wrappers."""

from __future__ import annotations

from ..residual_solver import solve_recycle_with_residual_minimization


def recycle_closure_correction(feed_kg_h: float, recycle_kg_h: float):
    """Return bounded recycle closure correction."""
    return solve_recycle_with_residual_minimization(feed_kg_h, recycle_kg_h)

