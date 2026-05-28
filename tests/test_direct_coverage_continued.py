from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np
import pandas as pd

from epdm_sim.audit_trail import AuditTrailRecord, create_audit_record, save_audit_to_sqlite
from epdm_sim.calibration import CalibrationResult, pdf_rules_dataframe
from epdm_sim.calibration_loop import CalibrationLoopResult, rank_parameters_by_uncertainty
from epdm_sim.case_manager import CaseRecord, case_path, case_record_from_json_bytes
from epdm_sim.cfd.boundary import BoundaryCondition, default_pipe_boundaries
from epdm_sim.cfd.fem_solver import fenicsx_available, selected_solver_mode
from epdm_sim.cfd.mesh import CFDGeometryConfig, StructuredMesh, create_mesh
from epdm_sim.cfd.transport import apply_pipe_inlet_outlet, normalized_active
from epdm_sim.conservation import ConservationDiagnostic, recycle_balance, total_mass_balance
from epdm_sim.db import connect, list_model_runs, save_json_record, save_model_run
from epdm_sim.dynamic_reactor import DynamicReactorConfig, DynamicReactorResult, dynamic_recommendations, stage_timeline
from epdm_sim.eos import binary_interaction, eos_details_table
from epdm_sim.equation_registry import EquationSpec, equations_by_module
from epdm_sim.equation_tests import EquationCodeCheck, equation_code_checks_dataframe
from epdm_sim.experiment_data import DataQualityReport, load_experiment_schema
from epdm_sim.identifiability import IdentifiabilityResult
from epdm_sim.kpi_schema import KPI, validate_kpi_bounds
from epdm_sim.layout_3d import process_3d_layout
from epdm_sim.model_contracts import ModelContract, get_model_contract
from epdm_sim.model_validation import ModelValidationIssue, validate_model_contract
from epdm_sim.ode_events import ODEEventRecord, event_log_dataframe
from epdm_sim.ode_jacobian import JacobianDiagnostic, scaled_finite_difference_jacobian
from epdm_sim.preflight import PreflightResult, preflight_dataframe
from epdm_sim.property_confidence import PropertySource, load_property_sources
from epdm_sim.repro_package import ReproPackageManifest, build_repro_manifest
from epdm_sim.scaleup import ScaleUpResult, default_tank_diameter
from epdm_sim.services.report_service import export_bundle, figure_export_status
from epdm_sim.services.task_service import TaskRecord, task_graph_dataframe
from epdm_sim.state_vector import StateVectorLayout, clamp_state_nonnegative
from epdm_sim.streams import Stream, mix_streams
from epdm_sim.template_config import process_config_to_template_config, template_config_dict
from epdm_sim.time_series_data import TimeSeriesValidationResult, load_time_series_csv_or_excel
from epdm_sim.flowsheet import load_default_config, run_flowsheet


def test_audit_case_db_and_calibration_helpers(tmp_path):
    record = create_audit_record("run", "task", {"x": 1}, {"y": 2}, runtime_s=0.01)
    assert isinstance(record, AuditTrailRecord)
    db_path = tmp_path / "audit.sqlite"
    assert save_audit_to_sqlite([record], str(db_path)) == 1

    case = CaseRecord("case_1", "Case 1", {"temperature_C": 50.0}, kpis={"polymer_kg_h": 1.0})
    payload = json.dumps(case.to_dict()).encode("utf-8")
    parsed = case_record_from_json_bytes(payload)
    assert parsed.case_id == "case_1"
    assert case_path("../bad id", tmp_path).parent == tmp_path

    conn = connect(tmp_path / "warehouse.sqlite")
    conn.close()
    save_model_run("run1", "flowsheet", {"polymer_kg_h": 1.0}, "hash", tmp_path / "warehouse.sqlite")
    save_json_record("parameter_sets", "set1", {"a": 1}, tmp_path / "warehouse.sqlite")
    runs = list_model_runs(tmp_path / "warehouse.sqlite")
    assert "run1" in set(runs["run_id"])

    rules = pdf_rules_dataframe()
    assert not rules.empty
    calibration = CalibrationResult(params={"k": 1.0}, residuals=pd.DataFrame({"r": [0.0]}), r2={"x": 1.0}, mae={"x": 0.0})
    assert calibration.params["k"] == 1.0


def test_conservation_streams_and_recycle_helpers():
    feed = Stream.from_mass_flows("Feed", 323.15, 1.0e6, {"hexane": 10.0})
    product = Stream.from_mass_flows("Polymer product", 323.15, 1.0e5, {"hexane": 8.0})
    vapor = Stream.from_mass_flows("Flash-1 vapor", 323.15, 1.0e5, {"hexane": 2.0}, phase="vapor")
    empty = Stream.from_mass_flows("Flash-2 vapor", 323.15, 1.0e5, {})
    result = SimpleNamespace(streams={"Feed": feed, "Polymer product": product, "Flash-1 vapor": vapor, "Flash-2 vapor": empty})
    balance = total_mass_balance(result, tolerance_pct=0.01)
    assert balance.passed
    assert balance.absolute_error == 0.0

    recycle = recycle_balance(SimpleNamespace(closure_error=0.2), tolerance_pct=1.0)
    assert recycle.passed
    diagnostic = ConservationDiagnostic("mass", "flash", "kg/h vs mol/h", "Flash-1", "check split", "warning")
    assert diagnostic.as_dict()["likely_source"] == "flash"

    mixed = mix_streams("mixed", [feed, vapor])
    assert mixed.total_mass_flow() == 12.0


def test_cfd_boundary_transport_and_solver_mode_helpers():
    boundaries = default_pipe_boundaries(0.4, 45.0, 101325.0)
    assert all(isinstance(item, BoundaryCondition) for item in boundaries)
    assert {item.name for item in boundaries} >= {"inlet", "outlet", "walls"}
    assert isinstance(fenicsx_available(), bool)
    assert selected_solver_mode("fenicsx") in {"FEniCSx", "Simple CFD"}

    mesh = create_mesh(CFDGeometryConfig(geometry_type="Pipe 2D", nx=20, ny=10))
    assert isinstance(mesh, StructuredMesh)
    field = np.ones(mesh.shape)
    bounded = apply_pipe_inlet_outlet(field, inlet_value=3.0, wall_value=0.0)
    assert np.allclose(bounded[1:-1, 0], 3.0)
    assert np.allclose(bounded[0, :], 0.0)
    norm = normalized_active(mesh, mesh.X)
    assert float(np.nanmin(norm)) >= 0.0
    assert float(np.nanmax(norm)) <= 1.0


def test_dynamic_eos_equation_and_kpi_helpers():
    stages = stage_timeline(60.0)
    assert stages["duration_min"].ge(0.0).all()
    profile = pd.DataFrame(
        {
            "fouling_index": [0.5, 0.8],
            "T_C": [50.0, 55.0],
            "C_ENB_mol_L": [0.1, 0.11],
            "impeller_Re": [200.0, 180.0],
        }
    )
    recs = dynamic_recommendations(profile, DynamicReactorConfig())
    assert recs and isinstance(recs[0], str)
    dyn = DynamicReactorResult(DynamicReactorConfig(), profile, stages, {"ok": True})
    assert dyn.time_profile().equals(profile)

    kij = binary_interaction("ethylene", "hexane")
    assert np.isfinite(kij)
    details = eos_details_table(["ethylene", "propylene"], 323.15, 1.0e6, eos="PR")
    assert details and all(row["K"] > 0.0 for row in details)
    mapping = equations_by_module()
    assert "reactor_kinetics" in mapping
    spec = EquationSpec("eq", "module", "name", "y=x", ["x"], {"x": "kg/h"}, "kg/h")
    assert spec.output_unit == "kg/h"
    check_df = equation_code_checks_dataframe([EquationCodeCheck("eq", "f", "trend", "finite", True, "ok")])
    assert bool(check_df.loc[0, "passed"])

    checked = validate_kpi_bounds([KPI("conversion", 120.0, "%", "reactor", "template", bounds=(0.0, 100.0))])
    assert "upper bound" in checked[0].warning


def test_schema_contract_preflight_property_and_time_series_helpers(tmp_path):
    schema = load_experiment_schema()
    assert "required_fields" in schema
    quality = DataQualityReport(missing_fields=["run_id"])
    assert "run_id" in quality.missing_fields

    contract = get_model_contract("flowsheet")
    issues = validate_model_contract(contract)
    assert isinstance(contract, ModelContract)
    assert all(isinstance(item, ModelValidationIssue) for item in issues)
    bad = PreflightResult("m", False, "error", "bad pressure", "pressure", -1.0, "Pa", ">0")
    df = preflight_dataframe([bad])
    assert df.loc[0, "severity"] == "error"

    sources = load_property_sources()
    assert sources and isinstance(sources[0], PropertySource)

    csv_path = tmp_path / "profile.csv"
    csv_path.write_text("run_id,time_min,temperature_C,pressure_MPa\nr1,0,50,1.0\nr1,1,51,1.0\n", encoding="utf-8")
    ts = load_time_series_csv_or_excel(csv_path)
    assert ts["time_min"].is_monotonic_increasing
    validation = TimeSeriesValidationResult(True, [], ["time_min"], list(ts.columns))
    assert validation.passed


def test_numerical_layout_state_report_and_repro_helpers():
    events = event_log_dataframe([ODEEventRecord(1.0, "quench", "stopped", "warning")])
    assert events.loc[0, "event_id"] == "quench"
    jac = scaled_finite_difference_jacobian(lambda _t, y: -y, 0.0, np.array([1.0, 2.0]), np.array([1.0, 2.0]))
    assert jac.shape == (2, 2)
    diag = JacobianDiagnostic(jac.shape, np.isfinite(jac).all(), float(np.max(np.abs(jac))), 1.0)
    assert diag.finite

    state = clamp_state_nonnegative({"liquid_moles": {"ethylene": -1.0}, "polymer_mass_kg": -2.0})
    assert state["liquid_moles"]["ethylene"] == 0.0
    layout = StateVectorLayout("template", ["ethylene"], ["ethylene"], ["E"], ["hydrogen"])
    assert "ethylene" in layout.liquid_moles

    fig = process_3d_layout(mode="risk")
    assert len(fig.data) > 0
    notes = figure_export_status({"layout": fig, "table": object()})
    assert len(notes) == 2

    cfg = load_default_config()
    result = run_flowsheet(cfg)
    excel = export_bundle(result, report_type="excel")
    assert isinstance(excel, bytes) and len(excel) > 1000
    manifest = build_repro_manifest(result, parameter_set={"id": "default"}, test_status="passed")
    assert isinstance(manifest, ReproPackageManifest)
    assert manifest.test_status == "passed"

    diameter = default_tank_diameter(5.0)
    assert diameter > 0.0
    scale = ScaleUpResult("2L", 2.0, 500.0, 0.08, 0.15, 0.1, 50.0, 1000.0, 2.0, 30.0, 1.0, 1.0, 5.0, "ok", "low", "low", "low", 500.0, 0.08, "ok")
    assert scale.power_kW > 0.0
    task = TaskRecord("flowsheet_fast", status="success")
    assert task.to_dict()["status"] == "success"
    assert not task_graph_dataframe().empty


def test_identifiability_loop_and_template_config_helpers():
    status = pd.DataFrame(
        [
            {"parameter": "beta_P", "sensitivity_norm": 1.0, "status": "weakly_identifiable", "reason": "test"},
            {"parameter": "ktr_H2", "sensitivity_norm": 1.0, "status": "identifiable", "reason": "test"},
        ]
    )
    ident = IdentifiabilityResult(
        sensitivity_matrix=pd.DataFrame({"parameter": ["beta_P"], "C2_wt": [1.0]}),
        parameter_correlation=pd.DataFrame([[1.0]], columns=["beta_P"], index=["beta_P"]),
        condition_number=1.0,
        status=status,
        warnings=[],
    )
    ranked = rank_parameters_by_uncertainty(ident)
    assert ranked.iloc[0]["parameter"] == "beta_P"
    loop = CalibrationLoopResult(
        current_parameter_set={"k": 1.0},
        fitted_metrics=pd.DataFrame({"metric": ["Mw"]}),
        identifiability_summary=status,
        uncertainty_summary=pd.DataFrame({"metric": ["Mw"], "p50": [1.0]}),
        recommended_experiments=pd.DataFrame({"experiment_id": ["x"]}),
        expected_information_gain=pd.DataFrame({"gain": [1.0]}),
        expected_risk_reduction=pd.DataFrame({"risk": ["fouling"]}),
    )
    assert set(loop.as_dataframe()["section"]) >= {"parameters", "identifiability"}

    cfg = load_default_config()
    template_cfg = process_config_to_template_config(cfg)
    payload = template_config_dict(template_cfg)
    assert payload["monomer_feeds_kg_h"]["ethylene"] == cfg.ethylene_kg_h
