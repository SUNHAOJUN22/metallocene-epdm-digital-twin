"""Lineage helpers for MCP-style external tool responses."""

from __future__ import annotations

from .schemas import LineageSnapshot, SimulationInput
from epdm_sim import APP_VERSION


def build_lineage_snapshot(tool_name: str, request: SimulationInput) -> LineageSnapshot:
    """Return a compact lineage snapshot for one external tool call."""
    return LineageSnapshot(
        source=request.source,
        model_version=APP_VERSION,
        tool_name=tool_name,
        dry_run=bool(request.dry_run),
        run_heavy_task=bool(request.run_heavy_task),
    )
