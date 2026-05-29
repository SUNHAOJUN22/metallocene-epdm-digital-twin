"""MCP-style governed tool functions for EPDM digital-twin integration."""

from __future__ import annotations

from typing import Any

import pandas as pd

from epdm_sim import APP_VERSION, __version__
from epdm_sim.aspen_bridge import aspen_bridge_summary
from epdm_sim.flowsheet import run_flowsheet
from epdm_sim.governance_certificate import governance_certificate_dataframe, governance_certificate_summary
from epdm_sim.residual_system import build_flowsheet_residual_system

from .adapters import build_process_config_from_payload, residual_summary_from_system, tool_result_from_exception
from .lineage import build_lineage_snapshot
from .safety import mcp_preflight_check
from .schemas import (
    DoeRequest,
    DynamicReactorRequest,
    FlashRequest,
    FlowsheetRequest,
    HeatBalanceRequest,
    OptimizerRequest,
    ReportSnapshotRequest,
    SimulationInput,
    ToolResult,
)


def _dump_tool_result(result: ToolResult) -> dict[str, Any]:
    """Return a dict from a pydantic result on v1 or v2 without warnings."""
    return result.model_dump() if hasattr(result, "model_dump") else result.dict()


def _request_from_payload(payload: dict[str, Any] | None, request_type: type[SimulationInput]) -> SimulationInput:
    return request_type(**(payload or {}))


def _preflight_result(tool_name: str, request: SimulationInput, task_id: str) -> tuple[bool, ToolResult | None]:
    passed, messages, validity = mcp_preflight_check(request, task_id)
    if not passed:
        return False, ToolResult(
            tool_name=tool_name,
            status="rejected",
            message="MCP preflight rejected the request.",
            data={"violations": messages},
            validity=validity,
            lineage=build_lineage_snapshot(tool_name, request),
            warnings=messages,
        )
    if request.dry_run:
        return False, ToolResult(
            tool_name=tool_name,
            status="not_run",
            message="Dry run completed; no scientific calculation or heavy task was executed.",
            data={"task_id": task_id, "preflight_passed": True},
            validity=validity,
            lineage=build_lineage_snapshot(tool_name, request),
            heavy_task_executed=False,
        )
    return True, None


def get_model_metadata(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return model metadata and external-tool contract flags without running science tasks."""
    _ = payload or {}
    return {
        "tool_name": "get_model_metadata",
        "status": "ok",
        "message": "Model metadata loaded without running heavy tasks.",
        "data": {
            "app_version": APP_VERSION,
            "package_version": __version__,
            "mcp_interface": "tool-only",
            "default_dry_run": True,
            "heavy_task_policy": "explicit run_heavy_task=True required",
            "non_replaceable_kernels": ["ResidualSystem", "flash/EOS", "ODE/DAE", "benchmark", "release_gate"],
        },
        "heavy_task_executed": False,
    }


def validate_simulation_input(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Validate unit, finite, validity and heavy-task policy for an external request."""
    request = _request_from_payload(payload, SimulationInput)
    passed, messages, validity = mcp_preflight_check(request, "validation")
    result = ToolResult(
        tool_name="validate_simulation_input",
        status="ok" if passed else "rejected",
        message="Input preflight passed." if passed else "Input preflight failed.",
        data={"violations": messages, "payload_keys": sorted(request.payload.keys())},
        validity=validity,
        lineage=build_lineage_snapshot("validate_simulation_input", request),
        warnings=messages,
    )
    return _dump_tool_result(result)


def run_flowsheet_simulation(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run or dry-run the flowsheet through MCP safety and ResidualSystem acceptance."""
    tool_name = "run_flowsheet_simulation"
    request = _request_from_payload(payload, FlowsheetRequest)
    should_run, early = _preflight_result(tool_name, request, request.task_id)
    if not should_run:
        return _dump_tool_result(early) if early is not None else {}
    try:
        config = build_process_config_from_payload(request.payload)
        result = run_flowsheet(config)
        system = build_flowsheet_residual_system(result)
        residual = residual_summary_from_system(system)
        status = "ok" if residual is not None and residual.passed else "rejected"
        data = {
            "kpis": dict(result.kpis),
            "warnings": list(result.warnings),
            "stream_count": len(result.streams),
        }
        tool_result = ToolResult(
            tool_name=tool_name,
            status=status,
            message="Flowsheet completed with ResidualSystem acceptance." if status == "ok" else "Flowsheet residual acceptance failed.",
            data=data,
            residual_summary=residual,
            lineage=build_lineage_snapshot(tool_name, request),
            heavy_task_executed=True,
            warnings=list(result.warnings),
        )
        return _dump_tool_result(tool_result)
    except Exception as exc:  # pragma: no cover - exercised via safety tests for rejection paths
        return _dump_tool_result(tool_result_from_exception(tool_name, exc))


def prepare_aspen_exchange(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Prepare Aspen exchange metadata without invoking Aspen COM automation."""
    tool_name = "prepare_aspen_exchange"
    request = _request_from_payload(payload, FlowsheetRequest)
    should_run, early = _preflight_result(tool_name, request, request.task_id)
    if not should_run:
        return _dump_tool_result(early) if early is not None else {}
    try:
        config = build_process_config_from_payload(request.payload)
        result = run_flowsheet(config)
        return _dump_tool_result(
            ToolResult(
                tool_name=tool_name,
                status="ok",
                message="Aspen exchange tables are ready; Aspen COM was not executed.",
                data=aspen_bridge_summary(result),
                lineage=build_lineage_snapshot(tool_name, request),
                heavy_task_executed=True,
                warnings=["Aspen execution remains manual or site-approved COM automation."],
            )
        )
    except Exception as exc:  # pragma: no cover
        return _dump_tool_result(tool_result_from_exception(tool_name, exc))


def run_flash_calculation(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Expose flash calculation as a governed dry-run endpoint for external clients."""
    tool_name = "run_flash_calculation"
    request = _request_from_payload(payload, FlashRequest)
    should_run, early = _preflight_result(tool_name, request, request.task_id)
    if not should_run:
        return _dump_tool_result(early) if early is not None else {}
    result = ToolResult(
        tool_name=tool_name,
        status="not_run",
        message="Flash execution is intentionally routed through flowsheet/release-gate paths in this interface.",
        data={"reason": "direct flash execution disabled for MCP safety boundary"},
        lineage=build_lineage_snapshot(tool_name, request),
        heavy_task_executed=False,
    )
    return _dump_tool_result(result)


def run_heat_balance(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Expose heat-balance calculation as a governed dry-run endpoint."""
    tool_name = "run_heat_balance"
    request = _request_from_payload(payload, HeatBalanceRequest)
    should_run, early = _preflight_result(tool_name, request, request.task_id)
    if not should_run:
        return _dump_tool_result(early) if early is not None else {}
    result = ToolResult(
        tool_name=tool_name,
        status="not_run",
        message="Heat-balance execution is routed through governed flowsheet paths.",
        data={"reason": "direct heat-balance execution disabled for MCP safety boundary"},
        lineage=build_lineage_snapshot(tool_name, request),
        heavy_task_executed=False,
    )
    return _dump_tool_result(result)


def run_dynamic_reactor(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Guard dynamic reactor entry so UI/action registry rules cannot be bypassed."""
    tool_name = "run_dynamic_reactor"
    request = _request_from_payload(payload, DynamicReactorRequest)
    should_run, early = _preflight_result(tool_name, request, request.task_id)
    if not should_run:
        return _dump_tool_result(early) if early is not None else {}
    result = ToolResult(
        tool_name=tool_name,
        status="not_run",
        message="Dynamic ODE/DAE runs must be triggered through TaskService/UI action registry.",
        data={"task_id": request.task_id},
        lineage=build_lineage_snapshot(tool_name, request),
        heavy_task_executed=False,
    )
    return _dump_tool_result(result)


def run_residual_aware_optimizer(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Guard optimizer entry so residual-critical candidates cannot bypass acceptance."""
    tool_name = "run_residual_aware_optimizer"
    request = _request_from_payload(payload, OptimizerRequest)
    should_run, early = _preflight_result(tool_name, request, request.task_id)
    if not should_run:
        return _dump_tool_result(early) if early is not None else {}
    result = ToolResult(
        tool_name=tool_name,
        status="not_run",
        message="Optimizer runs remain TaskService-triggered; MCP provides preflight only.",
        data={"task_id": request.task_id},
        lineage=build_lineage_snapshot(tool_name, request),
        heavy_task_executed=False,
    )
    return _dump_tool_result(result)


def run_residual_aware_doe(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Guard DOE entry so outside-validity candidates cannot bypass acceptance."""
    tool_name = "run_residual_aware_doe"
    request = _request_from_payload(payload, DoeRequest)
    should_run, early = _preflight_result(tool_name, request, request.task_id)
    if not should_run:
        return _dump_tool_result(early) if early is not None else {}
    result = ToolResult(
        tool_name=tool_name,
        status="not_run",
        message="DOE runs remain TaskService-triggered; MCP provides preflight only.",
        data={"task_id": request.task_id},
        lineage=build_lineage_snapshot(tool_name, request),
        heavy_task_executed=False,
    )
    return _dump_tool_result(result)


def generate_report_snapshot(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return report availability without rerunning heavy model paths."""
    tool_name = "generate_report_snapshot"
    request = _request_from_payload(payload, ReportSnapshotRequest)
    should_run, early = _preflight_result(tool_name, request, request.task_id)
    if not should_run:
        return _dump_tool_result(early) if early is not None else {}
    result = ToolResult(
        tool_name=tool_name,
        status="not_run",
        message="Report export must use existing results through the explicit UI action.",
        data={"missing_heavy_results": "not_run"},
        lineage=build_lineage_snapshot(tool_name, request),
        heavy_task_executed=False,
    )
    return _dump_tool_result(result)


def get_model_governance_certificate(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return model-governance certificate summaries without running heavy tasks."""
    _ = payload or {}
    frame = governance_certificate_dataframe()
    summary = governance_certificate_summary()
    records = frame.replace({pd.NA: None}).to_dict(orient="records")
    result = ToolResult(
        tool_name="get_model_governance_certificate",
        status="ok" if summary["passed"] else "warning",
        message="Governance certificate loaded without triggering heavy simulation tasks.",
        data={"summary": summary, "records": records},
        heavy_task_executed=False,
    )
    return _dump_tool_result(result)
