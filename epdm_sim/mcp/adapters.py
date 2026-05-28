"""Adapters between MCP contracts and existing EPDM digital-twin internals."""

from __future__ import annotations

from typing import Any

from epdm_sim.flowsheet import normalize_process_config
from epdm_sim.flowsheet_types import ProcessConfig
from epdm_sim.residual_system import ResidualSystem, residual_system_acceptance

from .schemas import ResidualSummary, ToolResult


def build_process_config_from_payload(payload: dict[str, Any]) -> ProcessConfig:
    """Build a process config from external payload data with legacy alias support."""
    return ProcessConfig(**normalize_process_config(payload))


def residual_summary_from_system(system: ResidualSystem | None) -> ResidualSummary | None:
    """Convert a ResidualSystem into a bounded MCP residual summary."""
    if system is None:
        return None
    acceptance = residual_system_acceptance(system)
    return ResidualSummary(
        passed=bool(acceptance["passed"]),
        overall_score=float(acceptance["overall_score"]),
        critical_count=int(acceptance["critical_count"]),
        error_count=int(acceptance["error_count"]),
        critical_sources=str(acceptance.get("critical_sources", "")),
    )


def tool_result_from_exception(tool_name: str, exc: Exception) -> ToolResult:
    """Convert an exception into a rejected external-tool result."""
    return ToolResult(tool_name=tool_name, status="rejected", message=str(exc), warnings=[type(exc).__name__])
