import math

from epdm_sim.calibrated_property_models import CalibratedPropertyModel
from epdm_sim.calibration_data_package import calibration_data_lineage_dataframe, load_calibration_data_package, validate_calibration_dataset_units
from epdm_sim.data_assimilation import assimilate_benchmark_observations, data_assimilation_summary, update_calibrated_model_from_evidence
from epdm_sim.dynamic_core.adaptive_step_control import adaptive_step_control_dataframe, adaptive_step_control_summary, adaptive_step_decision
from epdm_sim.dynamic_core.event_detection import detect_dynamic_events, dynamic_event_detection_dataframe, event_flags_summary
from epdm_sim.dynamic_template_reactor import simulate_template_semibatch_ode
from epdm_sim.flowsheet import run_flowsheet
from epdm_sim.model_confidence_certificate import confidence_certificate_dataframe, evidence_gap_priority_score, generate_model_confidence_certificate, validation_data_upgrade_plan
from epdm_sim.property_runtime_context import build_property_runtime_context, property_runtime_context_dataframe, property_runtime_context_summary
from epdm_sim.residual_aware_sampling import residual_aware_sample_weight, residual_aware_sampling_dataframe, residual_aware_sampling_decision
from epdm_sim.residual_system import ResidualSystem, build_flowsheet_residual_system, make_residual
from epdm_sim.solver_core.conservation_jacobian import conservation_jacobian_dataframe, estimate_conservation_jacobian, jacobian_condition_number, residual_vector_from_system
from epdm_sim.solver_core.equation_oriented_solver import (
    bounded_residual_newton_step,
    build_conservation_equation_system,
    equation_oriented_solver_certificate,
    equation_oriented_solver_gate,
    solve_equation_oriented_residuals,
)


def _models():
    return [
        CalibratedPropertyModel(
            model_id="exp_henry_v63",
            parameter_type="henry",
            parameters={"henry_multiplier": 1.2},
            dataset_id="exp_vle_v63",
            data_hash="hash_h63",
            validity_range={"temperature_C": [80.0, 130.0], "pressure_MPa": [0.5, 2.0]},
            uncertainty={"relative_pct": 0.05},
            source_type="experiment",
            confidence_score=88.0,
        ),
        CalibratedPropertyModel(
            model_id="exp_deltaH_v63",
            parameter_type="deltaH",
            parameters={"deltaH_kJ_mol": 108.0},
            dataset_id="exp_cal_v63",
            data_hash="hash_d63",
            validity_range={"temperature_C": [80.0, 130.0]},
            uncertainty={"relative_pct": 0.05},
            source_type="experiment",
            confidence_score=90.0,
        ),
    ]


def test_equation_oriented_solver_accepts_default_and_rejects_physical_errors():
    result = run_flowsheet()
    system = build_flowsheet_residual_system(result)
    equations = build_conservation_equation_system(system)
    solve = solve_equation_oriented_residuals(system)
    cert = equation_oriented_solver_certificate(system)
    gate = equation_oriented_solver_gate(system)
    jac = estimate_conservation_jacobian(variables=[0.0, 0.0])
    vec = residual_vector_from_system(system)
    step = bounded_residual_newton_step([0.01, -0.01], jac, max_step_norm=0.1)
    critical = ResidualSystem(phase_residuals=[make_residual("flash_polymer_vapor", "polymer vapor = 0", 0.1, 0.0, "kg/h", 1e-12, "flash", "inspect", "critical")])
    bad = solve_equation_oriented_residuals(critical)
    assert not equations.empty
    assert solve["accepted"]
    assert gate["passed"]
    assert not cert.empty and cert["passed"].astype(bool).all()
    assert step["finite"] and step["predicted_residual_norm_after"] <= step["predicted_residual_norm_before"]
    assert vec.size == len(system.all_residuals())
    assert math.isfinite(jacobian_condition_number(jac))
    assert not conservation_jacobian_dataframe(system).empty
    assert bad["polymer_vapor_violation"] and not bad["accepted"]


def test_data_assimilation_and_calibration_package_lineage():
    package = load_calibration_data_package(
        {
            "dataset_id": "plant_deltaH_v63",
            "source_type": "plant",
            "source_reference": "plant historian batch 2026-05",
            "measurement_unit": "kJ/h",
            "uncertainty": 0.04,
            "validity_range": {"temperature_C": [80.0, 130.0]},
            "confidence_level": "high",
            "observations": [{"name": "deltaH", "value": 110.0, "unit": "kJ/h"}],
        }
    )
    invalid = dict(package)
    invalid["measurement_unit"] = "bad_unit"
    assim = assimilate_benchmark_observations()
    summary = data_assimilation_summary()
    model = update_calibrated_model_from_evidence(package, parameter_type="deltaH", parameter_name="deltaH")
    lineage = calibration_data_lineage_dataframe(package)
    assert validate_calibration_dataset_units(package)["passed"]
    assert not validate_calibration_dataset_units(invalid)["passed"]
    assert not assim.empty
    assert summary["passed"]
    assert model.source_type == "plant" and model.confidence_score > 70.0
    assert not lineage.empty and lineage["data_hash"].astype(str).str.len().iloc[0] > 0


def test_property_runtime_context_keeps_residuals_accepted():
    result = run_flowsheet()
    base = property_runtime_context_dataframe(result, conditions={"temperature_C": 100.0, "pressure_MPa": 1.0}, models=_models(), enable_calibrated=False)
    calibrated = property_runtime_context_dataframe(result, conditions={"temperature_C": 100.0, "pressure_MPa": 1.0}, models=_models())
    context = build_property_runtime_context(result, conditions={"temperature_C": 100.0, "pressure_MPa": 1.0}, models=_models())
    summary = property_runtime_context_summary(result, conditions={"temperature_C": 100.0, "pressure_MPa": 1.0}, models=_models())
    assert not base.empty and not calibrated.empty
    assert calibrated["runtime_changed_count"].iloc[0] >= base["runtime_changed_count"].iloc[0]
    assert context["passed"] and summary["passed"]
    assert calibrated["finite_runtime"].astype(bool).all()


def test_dynamic_adaptive_step_control_and_event_detection():
    dynamic = simulate_template_semibatch_ode(solver_mode="explicit_bounded", total_time_min=4.0, dt_min=0.5)
    ok = adaptive_step_decision(0.0)
    bad = adaptive_step_decision(1.0, event_risk="runaway")
    steps = adaptive_step_control_dataframe(dynamic)
    summary = adaptive_step_control_summary(dynamic)
    events = dynamic_event_detection_dataframe(dynamic)
    raw_events = detect_dynamic_events(dynamic)
    flags = event_flags_summary(dynamic)
    assert ok["accepted"] and bad["rejected"]
    assert not steps.empty
    assert 0 <= summary["accepted_steps"] <= summary["rows"]
    assert not events.empty
    assert raw_events
    assert flags["event_count"] >= 1


def test_residual_aware_sampling_rejects_critical_and_bounds_risk():
    system = build_flowsheet_residual_system(run_flowsheet())
    critical = ResidualSystem(mass_residuals=[make_residual("bad", "in=out", 10.0, 0.0, "kg/h", 0.1, "reactor", "inspect", "critical")])
    ok = residual_aware_sampling_decision({"sample_id": "h2", "hydrogen_g_h": 8.0, "pressure_MPa": 1.5, "temperature_C": 100.0}, system)
    bad = residual_aware_sampling_decision({"sample_id": "bad", "pressure_MPa": 100.0, "temperature_C": 100.0}, system)
    critical_weight = residual_aware_sample_weight(critical)
    df = residual_aware_sampling_dataframe(result_or_system=system)
    assert ok["passed"]
    assert bad["rejected"]
    assert critical_weight["rejected"] and critical_weight["weight"] == 0.0
    assert not df.empty
    assert df["uncertainty_risk_probability"].between(0.0, 1.0).all()


def test_model_confidence_certificate_and_upgrade_plan():
    cert = generate_model_confidence_certificate()
    df = confidence_certificate_dataframe()
    gaps = evidence_gap_priority_score()
    plan = validation_data_upgrade_plan()
    assert cert["passed"]
    assert 0.0 <= cert["confidence_score"] <= 100.0
    assert not df.empty
    assert not gaps.empty and "VLE/flash recovery" in set(gaps.get("gap_id", []))
    assert not plan.empty
