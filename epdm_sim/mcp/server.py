"""Minimal in-process MCP-style tool registry for scientific integrations."""

from __future__ import annotations

from typing import Any, Callable

from .tools import (
    generate_report_snapshot,
    get_model_governance_certificate,
    get_model_metadata,
    run_dynamic_reactor,
    run_flash_calculation,
    run_flowsheet_simulation,
    run_heat_balance,
    run_residual_aware_doe,
    run_residual_aware_optimizer,
    validate_simulation_input,
)


MCP_TOOL_MAP: dict[str, Callable[[dict[str, Any] | None], dict[str, Any]]] = {
    "get_model_metadata": get_model_metadata,
    "validate_simulation_input": validate_simulation_input,
    "run_flowsheet_simulation": run_flowsheet_simulation,
    "run_flash_calculation": run_flash_calculation,
    "run_heat_balance": run_heat_balance,
    "run_dynamic_reactor": run_dynamic_reactor,
    "run_residual_aware_optimizer": run_residual_aware_optimizer,
    "run_residual_aware_doe": run_residual_aware_doe,
    "generate_report_snapshot": generate_report_snapshot,
    "get_model_governance_certificate": get_model_governance_certificate,
}


def mcp_tool_registry() -> list[dict[str, Any]]:
    """Return auditable MCP-style tool metadata."""
    return [
        {
            "name": name,
            "description": getattr(func, "__doc__", "").strip().splitlines()[0],
            "default_dry_run": name.startswith("run_") or name == "generate_report_snapshot",
            "requires_explicit_heavy_permission": name.startswith("run_") or name == "generate_report_snapshot",
        }
        for name, func in sorted(MCP_TOOL_MAP.items())
    ]


def call_mcp_tool(name: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Call a registered MCP-style tool by name."""
    if name not in MCP_TOOL_MAP:
        return {
            "tool_name": name,
            "status": "rejected",
            "message": f"Unknown MCP tool {name!r}.",
            "data": {"known_tools": sorted(MCP_TOOL_MAP)},
            "heavy_task_executed": False,
        }
    return MCP_TOOL_MAP[name](payload or {})
