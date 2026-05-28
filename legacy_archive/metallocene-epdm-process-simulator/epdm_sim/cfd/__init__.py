"""Lightweight CFD/FEM-style visualization module for EPDM process simulation."""

from .mesh import CFDGeometryConfig, StructuredMesh, create_mesh
from .simple_solver import CFDInput, SimpleCFDResult, run_simple_cfd

__all__ = [
    "CFDGeometryConfig",
    "StructuredMesh",
    "create_mesh",
    "CFDInput",
    "SimpleCFDResult",
    "run_simple_cfd",
]
