"""MCP-style scientific simulation interface for governed external tools."""

from .server import call_mcp_tool, mcp_tool_registry
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

__all__ = [
    "call_mcp_tool",
    "generate_report_snapshot",
    "get_model_governance_certificate",
    "get_model_metadata",
    "mcp_tool_registry",
    "run_dynamic_reactor",
    "run_flash_calculation",
    "run_flowsheet_simulation",
    "run_heat_balance",
    "run_residual_aware_doe",
    "run_residual_aware_optimizer",
    "validate_simulation_input",
]
