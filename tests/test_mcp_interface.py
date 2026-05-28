from epdm_sim.mcp import (
    call_mcp_tool,
    generate_report_snapshot,
    get_model_governance_certificate,
    get_model_metadata,
    mcp_tool_registry,
    run_dynamic_reactor,
    run_flash_calculation,
    run_flowsheet_simulation,
    run_heat_balance,
    run_residual_aware_doe,
    run_residual_aware_optimizer,
    validate_simulation_input,
)
from epdm_sim.mcp.server import MCP_TOOL_MAP


def test_mcp_metadata_and_registry_are_available_without_heavy_tasks():
    metadata = get_model_metadata({})
    assert metadata["status"] == "ok"
    assert not metadata["heavy_task_executed"]
    registry = mcp_tool_registry()
    assert registry
    assert "run_flowsheet_simulation" in MCP_TOOL_MAP
    assert call_mcp_tool("get_model_metadata", {})["status"] == "ok"
    assert call_mcp_tool("missing_tool", {})["status"] == "rejected"


def test_mcp_validation_rejects_bad_unit_and_accepts_valid_context():
    rejected = validate_simulation_input({"units": {"pressure": "bar"}, "payload": {"temperature_C": 80.0}})
    assert rejected["status"] == "rejected"
    accepted = validate_simulation_input({"payload": {"temperature_C": 80.0, "pressure_MPa": 1.0}})
    assert accepted["status"] == "ok"


def test_mcp_scientific_tools_default_to_dry_run_no_heavy_execution():
    payload = {"payload": {"temperature_C": 90.0, "pressure_MPa": 1.0}}
    for tool in [
        run_flowsheet_simulation,
        run_flash_calculation,
        run_heat_balance,
        run_dynamic_reactor,
        run_residual_aware_optimizer,
        run_residual_aware_doe,
        generate_report_snapshot,
    ]:
        result = tool(payload)
        assert result["status"] == "not_run"
        assert result["heavy_task_executed"] is False


def test_mcp_heavy_task_requires_explicit_permission():
    result = run_dynamic_reactor({"dry_run": False, "run_heavy_task": False})
    assert result["status"] == "rejected"
    assert not result["heavy_task_executed"]
    assert "violations" in result["data"]


def test_mcp_flowsheet_explicit_run_returns_bounded_residual_summary():
    result = run_flowsheet_simulation(
        {
            "dry_run": False,
            "run_heavy_task": True,
            "payload": {"temperature_C": 100.0, "pressure_MPa": 1.0},
        }
    )
    assert result["heavy_task_executed"] is True
    assert result["residual_summary"]["critical_count"] == 0
    assert 0.0 <= result["residual_summary"]["overall_score"] <= 100.0


def test_mcp_governance_certificate_is_reportable_without_heavy_task():
    result = get_model_governance_certificate({})
    assert result["status"] in {"ok", "warning"}
    assert not result["heavy_task_executed"]
    assert result["data"]["summary"]["rows"] > 0
