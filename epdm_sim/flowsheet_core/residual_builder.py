"""Flowsheet residual builder wrappers."""

from __future__ import annotations

from ..residual_system import build_flowsheet_residual_system


def build_flowsheet_residuals(result):
    """Build a ResidualSystem from a flowsheet result."""
    return build_flowsheet_residual_system(result)

