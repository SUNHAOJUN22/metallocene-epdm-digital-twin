"""Optional FEniCSx solver facade.

The MVP uses the lightweight solver by default. This module only detects
whether dolfinx/FEniCSx is available so the UI can report the active mode.
"""

from __future__ import annotations

import importlib.util


def fenicsx_available() -> bool:
    """Return True when dolfinx appears importable."""
    return importlib.util.find_spec("dolfinx") is not None


def selected_solver_mode(requested_mode: str) -> str:
    """Return the actual CFD solver mode used by the application."""
    if requested_mode == "FEniCSx FEM" and fenicsx_available():
        return "FEniCSx FEM"
    return "Simple CFD"
