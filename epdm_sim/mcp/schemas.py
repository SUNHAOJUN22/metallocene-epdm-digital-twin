"""Schema contracts for the MCP-style EPDM digital-twin interface."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class UnitContext(BaseModel):
    """Explicit unit context required at all MCP model-entry boundaries."""

    pressure: str = "MPa"
    temperature: str = "C"
    concentration: str = "mol/m3"
    power: str = "kW"
    viscosity: str = "Pa.s"
    mass_flow: str = "kg/h"
    molar_flow: str = "mol/h"


class SimulationInput(BaseModel):
    """Common guarded simulation input envelope for external tool calls."""

    payload: dict[str, Any] = Field(default_factory=dict)
    units: UnitContext = Field(default_factory=UnitContext)
    dry_run: bool = True
    run_heavy_task: bool = False
    require_validity: bool = True
    source: str = "mcp"


class FlowsheetRequest(SimulationInput):
    """Flowsheet request envelope."""

    task_id: str = "flowsheet_fast"


class FlashRequest(SimulationInput):
    """Flash calculation request envelope."""

    task_id: str = "flash_calculation"


class HeatBalanceRequest(SimulationInput):
    """Heat-balance request envelope."""

    task_id: str = "heat_balance"


class DynamicReactorRequest(SimulationInput):
    """Dynamic reactor request envelope."""

    task_id: str = "dynamic_template_ode"


class OptimizerRequest(SimulationInput):
    """Residual-aware optimizer request envelope."""

    task_id: str = "optimization"


class DoeRequest(SimulationInput):
    """Residual-aware DOE request envelope."""

    task_id: str = "bayesian_doe"


class ReportSnapshotRequest(SimulationInput):
    """Report snapshot request envelope that must not trigger heavy recomputation."""

    task_id: str = "report_export"


class ResidualSummary(BaseModel):
    """Bounded residual-system summary returned to external tools."""

    passed: bool
    overall_score: float
    critical_count: int
    error_count: int
    critical_sources: str = ""


class ValidityStatus(BaseModel):
    """Validity-envelope status for an external tool call."""

    passed: bool
    outside_validity: bool = False
    messages: list[str] = Field(default_factory=list)


class LineageSnapshot(BaseModel):
    """Compact lineage fields carried by external tool results."""

    source: str = "mcp"
    model_version: str
    tool_name: str
    dry_run: bool
    run_heavy_task: bool


class ToolResult(BaseModel):
    """Serializable tool-call result for MCP clients."""

    tool_name: str
    status: str
    message: str
    data: dict[str, Any] = Field(default_factory=dict)
    residual_summary: ResidualSummary | None = None
    validity: ValidityStatus | None = None
    lineage: LineageSnapshot | None = None
    heavy_task_executed: bool = False
    warnings: list[str] = Field(default_factory=list)
