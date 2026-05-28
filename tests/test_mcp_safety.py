import math

from epdm_sim.mcp.adapters import build_process_config_from_payload, residual_summary_from_system, tool_result_from_exception
from epdm_sim.mcp.lineage import build_lineage_snapshot
from epdm_sim.mcp.safety import (
    mcp_preflight_check,
    reject_heavy_task_without_explicit_permission,
    reject_invalid_units,
    reject_nan_inf_input,
    reject_negative_absolute_temperature,
    reject_outside_validity_if_required,
)
from epdm_sim.mcp.schemas import (
    DoeRequest,
    DynamicReactorRequest,
    FlashRequest,
    FlowsheetRequest,
    HeatBalanceRequest,
    LineageSnapshot,
    OptimizerRequest,
    ReportSnapshotRequest,
    ResidualSummary,
    SimulationInput,
    ToolResult,
    UnitContext,
    ValidityStatus,
)
from epdm_sim.residual_system import ResidualSystem


def test_mcp_schema_classes_are_constructible():
    unit_context = UnitContext()
    requests = [
        SimulationInput(units=unit_context),
        FlowsheetRequest(units=unit_context),
        FlashRequest(units=unit_context),
        HeatBalanceRequest(units=unit_context),
        DynamicReactorRequest(units=unit_context),
        OptimizerRequest(units=unit_context),
        DoeRequest(units=unit_context),
        ReportSnapshotRequest(units=unit_context),
    ]
    assert all(request.dry_run for request in requests)
    assert ResidualSummary(passed=True, overall_score=100.0, critical_count=0, error_count=0).passed
    assert ValidityStatus(passed=True).passed
    assert LineageSnapshot(model_version="Vx", tool_name="tool", dry_run=True, run_heavy_task=False).dry_run
    assert ToolResult(tool_name="tool", status="ok", message="ok").status == "ok"


def test_mcp_preflight_rejects_invalid_units_nan_temperature_and_heavy_task():
    request = SimulationInput(
        payload={"temperature_K": -1.0, "pressure_MPa": math.inf},
        units=UnitContext(pressure="bar"),
        dry_run=False,
        run_heavy_task=False,
    )
    passed, violations, validity = mcp_preflight_check(request, "dynamic_template_ode")
    assert not passed
    assert not validity.passed
    assert any("unsupported pressure" in item for item in violations)
    assert any("not finite" in item for item in violations)
    assert any("above 0 K" in item for item in violations)
    assert any("requires run_heavy_task=True" in item for item in violations)


def test_mcp_safety_helpers_cover_unit_finite_validity_and_task_policy():
    assert reject_invalid_units({"pressure": "bar", "temperature": "C"})
    assert reject_nan_inf_input({"a": [1.0, float("nan")]})
    assert reject_negative_absolute_temperature({"temperature_C": -300.0}, {"temperature": "C"})
    status = reject_outside_validity_if_required({"pressure_MPa": 50.0}, True)
    assert status.outside_validity
    assert reject_heavy_task_without_explicit_permission("optimization", run_heavy_task=False, dry_run=False)


def test_mcp_adapters_return_config_residual_summary_and_exception_result():
    config = build_process_config_from_payload({"temperature_C": 90.0, "pressure_MPa": 1.2})
    assert config.temperature_C == 90.0
    summary = residual_summary_from_system(ResidualSystem(overall_score=100.0))
    assert summary is not None and summary.passed and summary.critical_count == 0
    result = tool_result_from_exception("tool", ValueError("bad"))
    assert result.status == "rejected"


def test_mcp_lineage_snapshot_records_version_and_policy():
    request = SimulationInput(source="unit-test", dry_run=True, run_heavy_task=False)
    snapshot = build_lineage_snapshot("validate", request)
    assert snapshot.source == "unit-test"
    assert snapshot.tool_name == "validate"
