import math

from epdm_sim.calibrated_property_models import CalibratedPropertyModel
from epdm_sim.dynamic_core.solver_policy import choose_dynamic_solver_policy, dynamic_solver_policy_dataframe, dynamic_solver_policy_report
from epdm_sim.dynamic_core.step_acceptance import dynamic_step_acceptance_dataframe, dynamic_step_acceptance_record, dynamic_step_acceptance_summary
from epdm_sim.dynamic_template_reactor import simulate_template_semibatch_ode
from epdm_sim.evidence_chain_score import critical_evidence_chain_gate, evidence_chain_score, evidence_chain_score_dataframe, evidence_gap_priority_dataframe
from epdm_sim.flowsheet import run_flowsheet
from epdm_sim.property_model_runtime import (
    property_model_runtime_dataframe,
    runtime_flash_k_values,
    runtime_heat_release,
    runtime_henry_cstar,
    runtime_rheology_viscosity,
)
from epdm_sim.residual_aware_doe import filter_residual_aware_doe_candidates, residual_aware_doe_candidate_score, residual_aware_doe_dataframe
from epdm_sim.residual_aware_optimizer import reject_optimizer_candidate, residual_aware_optimizer_dataframe, residual_aware_optimizer_objective
from epdm_sim.residual_system import ResidualSystem, build_flowsheet_residual_system, make_residual
from epdm_sim.solver_core.conservation_solve_path import (
    apply_conservation_corrections_to_flowsheet,
    conservation_solve_certificate_dataframe,
    solve_flash_with_mass_closure,
    solve_heat_balance_with_energy_closure,
    solve_recycle_with_residual_acceptance,
)


def _calibrated_models():
    return [
        CalibratedPropertyModel(
            model_id="exp_henry",
            parameter_type="henry",
            parameters={"henry_multiplier": 1.25},
            dataset_id="exp_vle",
            data_hash="hash_h",
            validity_range={"temperature_C": [80.0, 130.0], "pressure_MPa": [0.5, 2.0]},
            uncertainty={"relative_pct": 0.05},
            source_type="experiment",
            confidence_score=88.0,
        ),
        CalibratedPropertyModel(
            model_id="exp_visc",
            parameter_type="viscosity",
            parameters={"viscosity_multiplier": 1.4},
            dataset_id="exp_rheo",
            data_hash="hash_v",
            validity_range={"temperature_C": [80.0, 130.0], "solids_wt": [5.0, 20.0]},
            uncertainty={"relative_pct": 0.08},
            source_type="experiment",
            confidence_score=86.0,
        ),
        CalibratedPropertyModel(
            model_id="exp_flash_k",
            parameter_type="flash_k",
            parameters={"flash_k_multiplier": 1.1},
            dataset_id="exp_flash",
            data_hash="hash_f",
            validity_range={"temperature_C": [80.0, 130.0], "pressure_MPa": [0.5, 2.0]},
            uncertainty={"relative_pct": 0.10},
            source_type="experiment",
            confidence_score=82.0,
        ),
        CalibratedPropertyModel(
            model_id="exp_deltaH",
            parameter_type="deltaH",
            parameters={"deltaH_kJ_mol": 110.0},
            dataset_id="exp_calorimetry",
            data_hash="hash_d",
            validity_range={"temperature_C": [80.0, 130.0]},
            uncertainty={"relative_pct": 0.06},
            source_type="experiment",
            confidence_score=90.0,
        ),
    ]


def test_conservation_solve_path_closes_small_and_rejects_physical_errors():
    result = run_flowsheet()
    system = build_flowsheet_residual_system(result)
    summary = apply_conservation_corrections_to_flowsheet(system)
    cert = conservation_solve_certificate_dataframe(system)
    assert summary["accepted"]
    assert not cert.empty
    assert not cert.get("rejected").astype(bool).any()
    small_flash = solve_flash_with_mass_closure(100.0, 20.0, 79.99, tolerance=0.02)
    large_flash = solve_flash_with_mass_closure(100.0, 20.0, 60.0, tolerance=0.02)
    polymer_vapor = solve_flash_with_mass_closure(100.0, 20.0, 80.0, polymer_vapor=0.1)
    heat_bad = solve_heat_balance_with_energy_closure(10.0, -10.0)
    recycle = solve_recycle_with_residual_acceptance(100.0, 99.99, tolerance=0.02)
    assert small_flash["accepted"]
    assert large_flash["rejected"]
    assert polymer_vapor["severity"] == "critical"
    assert heat_bad["rejected"]
    assert recycle["accepted"]


def test_property_model_runtime_changes_values_and_preserves_trends():
    models = _calibrated_models()
    henry_base = runtime_henry_cstar(partial_pressure_MPa=1.0, models=models, enable_calibrated=False)
    henry_cal = runtime_henry_cstar(partial_pressure_MPa=1.0, models=models)
    henry_high_p = runtime_henry_cstar(partial_pressure_MPa=1.5, models=models)
    visc_base = runtime_rheology_viscosity(models=models, enable_calibrated=False)
    visc_cal = runtime_rheology_viscosity(models=models)
    heat_base = runtime_heat_release(models=models, enable_calibrated=False)
    heat_cal = runtime_heat_release(models=models)
    flash = runtime_flash_k_values(models=models)
    fallback = runtime_henry_cstar(temperature_K=500.0, partial_pressure_MPa=1.0, models=models)
    df = property_model_runtime_dataframe(conditions={"temperature_C": 100.0, "pressure_MPa": 1.0, "solids_wt": 10.0}, models=models)
    assert henry_cal["runtime_value"] > henry_base["runtime_value"]
    assert henry_high_p["runtime_value"] > henry_cal["runtime_value"]
    assert visc_cal["runtime_value"] > visc_base["runtime_value"]
    assert heat_cal["runtime_heat_kJ_h"] > heat_base["runtime_heat_kJ_h"]
    assert flash["adjusted_k_values"]["hydrogen"] > 0.0
    assert flash["adjusted_k_values"]["polymer_EPDM"] <= 1.0e-9
    assert fallback["mode"] == "validity_fallback"
    assert not df.empty and df["passed"].astype(bool).all()


def test_dynamic_solver_policy_and_step_acceptance_are_bounded():
    default_policy = choose_dynamic_solver_policy(stiffness_indicator=10.0, residual_acceptance_rate=1.0)
    stiff_policy = choose_dynamic_solver_policy(stiffness_indicator=1.0e6, residual_acceptance_rate=1.0)
    fallback_policy = choose_dynamic_solver_policy(stiffness_indicator=10.0, residual_acceptance_rate=0.1)
    step_ok = dynamic_step_acceptance_record(1, 1.0e-8)
    step_bad = dynamic_step_acceptance_record(2, 1.0, event_risk="cooling_failure")
    dynamic = simulate_template_semibatch_ode(solver_mode="explicit_bounded", total_time_min=4.0, dt_min=0.5)
    steps = dynamic_step_acceptance_dataframe(dynamic)
    report = dynamic_solver_policy_report(dynamic)
    assert default_policy["selected_solver"] == "solve_ivp_rk45"
    assert stiff_policy["selected_solver"] == "solve_ivp_bdf"
    assert fallback_policy["fallback_recommended"]
    assert step_ok["accepted"] and not step_bad["accepted"]
    assert not steps.empty
    assert 0.0 <= dynamic_step_acceptance_summary(dynamic)["step_acceptance_rate"] <= 1.0
    assert not dynamic_solver_policy_dataframe(dynamic).empty
    assert report["selected_solver"] in {"solve_ivp_rk45", "solve_ivp_bdf", "explicit_bounded"}


def test_residual_aware_optimizer_and_doe_reject_bad_candidates():
    result = run_flowsheet()
    system = build_flowsheet_residual_system(result)
    critical = ResidualSystem(mass_residuals=[make_residual("bad", "in=out", 100.0, 0.0, "kg/h", 0.1, "flash", "inspect", "critical")])
    ok_obj = residual_aware_optimizer_objective(-1.0, system)
    bad_obj = residual_aware_optimizer_objective(-1.0, critical)
    bad_candidate = reject_optimizer_candidate({"temperature_C": 1000.0, "pressure_MPa": 1.0}, system)
    doe_ok = residual_aware_doe_candidate_score({"candidate_id": "h2", "hydrogen_g_h": 8.0, "pressure_MPa": 1.5, "temperature_C": 100.0}, system)
    doe_bad = residual_aware_doe_candidate_score({"candidate_id": "bad", "pressure_MPa": 100.0, "temperature_C": 100.0}, system)
    filtered = filter_residual_aware_doe_candidates([{"candidate_id": "h2", "hydrogen_g_h": 8.0}], system)
    assert ok_obj["passed"] and bad_obj["rejected"]
    assert bad_candidate["rejected"]
    assert doe_ok["recommended"]
    assert doe_bad["rejected"]
    assert not filtered.empty
    assert not residual_aware_optimizer_dataframe(system).empty
    assert not residual_aware_doe_dataframe(system).empty


def test_evidence_chain_score_and_gap_priorities_are_meaningful():
    score = evidence_chain_score()
    gate = critical_evidence_chain_gate()
    df = evidence_chain_score_dataframe()
    gaps = evidence_gap_priority_dataframe()
    assert 0.0 <= score["score"] <= 100.0
    assert gate["passed"]
    assert not df.empty
    assert {"VLE/flash recovery", "reaction calorimetry", "solution rheology", "GPC/Mooney", "dynamic T/P profile", "plant mass balance reconciliation"}.issubset(set(gaps["detail"]))
    assert math.isfinite(float(df["score"].iloc[0]))
