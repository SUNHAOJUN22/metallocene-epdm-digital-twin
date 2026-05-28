import math

import pandas as pd

from epdm_sim.calibrated_property_models import CalibratedPropertyModel
from epdm_sim.dynamic_core.event_certificates import event_certificate, event_certificate_dataframe
from epdm_sim.dynamic_core.invariant_projection import invariant_projection_dataframe, project_state_invariants
from epdm_sim.dynamic_core.solver_decision import (
    choose_dynamic_solver,
    dynamic_fallback_policy,
    dynamic_solver_decision_dataframe,
    residual_based_step_acceptance,
)
from epdm_sim.estimation.fit_diagnostics import fit_diagnostics_dataframe, fit_diagnostics_record
from epdm_sim.estimation.fit_runner import fit_runner_dataframe, run_fit_with_residual_constraints
from epdm_sim.estimation.physical_penalties import physical_penalty, physical_penalty_breakdown
from epdm_sim.estimation.residual_objectives import combined_residual_objective, residual_objectives_dataframe, weighted_data_residual
from epdm_sim.evidence_chain import (
    build_evidence_chain,
    evidence_gap_dataframe,
    evidence_weighted_confidence,
    recommend_evidence_upgrade,
    validate_evidence_chain_completeness,
)
from epdm_sim.flowsheet import run_flowsheet
from epdm_sim.flowsheet_core.energy_closure import energy_closure_dataframe, energy_closure_record
from epdm_sim.flowsheet_core.kpi_projection import kpi_projection_dataframe, project_kpis_with_bounds
from epdm_sim.flowsheet_core.material_closure import material_closure_dataframe, material_closure_record
from epdm_sim.flowsheet_core.unit_residuals import unit_residuals_dataframe
from epdm_sim.fluid_core.property_selector_bridge import fluid_property_bridge_dataframe
from epdm_sim.fluid_core.transport_residuals import transport_residuals_dataframe
from epdm_sim.property_model_bridge import bridge_property_value, property_bridge_confidence_adjustment, property_model_bridge_dataframe
from epdm_sim.reactor_core.heat_release import heat_release_dataframe, heat_release_from_conversion
from epdm_sim.reactor_core.polymer_moments import polymer_moment_estimates, polymer_moments_dataframe
from epdm_sim.reactor_core.reaction_balance import reaction_balance_dataframe, reaction_mass_balance_record
from epdm_sim.reactor_core.reactor_residuals import reactor_residuals_dataframe
from epdm_sim.residual_aware_decision import (
    reject_residual_critical_candidate,
    residual_aware_decision_dataframe,
    residual_aware_doe_score,
    residual_aware_posterior_weight,
    residual_aware_uncertainty_risk,
    residual_risk_score,
)
from epdm_sim.residual_system import ResidualSystem, build_flowsheet_residual_system, make_residual
from epdm_sim.solver_core.conservation_correction import (
    close_flash_split_residual,
    close_small_energy_residual,
    close_small_mass_residual,
    correction_certificate_dataframe,
    reject_large_residual_correction,
)


def test_conservation_correction_rejects_large_physical_mismatch():
    small = make_residual("mass_small", "in=out", 100.0, 99.95, "kg/h", 0.1, "flash", "inspect")
    large = make_residual("mass_large", "in=out", 100.0, 80.0, "kg/h", 0.1, "flash", "inspect", "critical")
    small_corr = close_small_mass_residual(small, max_relative_pct=0.1)
    large_corr = close_small_mass_residual(large, max_relative_pct=0.1)
    assert small_corr["accepted"]
    assert reject_large_residual_correction(large_corr)
    assert close_small_energy_residual(small)["accepted"]
    assert close_flash_split_residual(100.0, 20.0, 79.99, tolerance=0.02)["accepted"]
    df = correction_certificate_dataframe(ResidualSystem(mass_residuals=[small], energy_residuals=[small]))
    assert not df.empty
    assert "relative_error_pct" in df.columns


def test_property_model_bridge_changes_values_with_valid_calibration():
    models = [
        CalibratedPropertyModel(
            model_id="exp_viscosity",
            parameter_type="viscosity",
            parameters={"viscosity_multiplier": 1.4},
            dataset_id="exp_visc",
            data_hash="abc",
            validity_range={"temperature_C": [80.0, 140.0]},
            uncertainty={"relative_pct": 0.1},
            source_type="experiment",
            confidence_score=88.0,
        )
    ]
    bridged = bridge_property_value(2.0, parameter_type="viscosity", parameter_name="viscosity", conditions={"temperature_C": 100.0}, models=models)
    fallback = bridge_property_value(2.0, parameter_type="viscosity", parameter_name="viscosity", conditions={"temperature_C": 200.0}, models=models)
    assert math.isclose(bridged["bridged_value"], 2.8)
    assert fallback["bridged_value"] == 2.0
    assert property_model_bridge_dataframe(conditions={"temperature_C": 100.0}, models=models).shape[0] == 4
    assert property_bridge_confidence_adjustment(conditions={"temperature_C": 100.0}, models=models)["passed"]
    assert not fluid_property_bridge_dataframe(100.0).empty


def test_dynamic_solver_decision_and_projection_helpers():
    rk = choose_dynamic_solver(stiffness_indicator=10.0, residual_acceptance_rate=1.0)
    bdf = choose_dynamic_solver(stiffness_indicator=1.0e6, residual_acceptance_rate=1.0)
    fallback = choose_dynamic_solver(stiffness_indicator=10.0, residual_acceptance_rate=0.1)
    assert rk["selected_solver"] == "solve_ivp_rk45"
    assert bdf["selected_solver"] == "solve_ivp_bdf"
    assert fallback["fallback_recommended"]
    assert dynamic_fallback_policy({"critical_residual_count": 1})["fallback_required"]
    assert residual_based_step_acceptance(1.0e-8)["accepted"]
    assert not dynamic_solver_decision_dataframe().empty
    projection = project_state_invariants({"T_K": -1.0, "P_Pa": -2.0, "polymer_mass_kg": -3.0})
    assert projection["corrections"] == 3
    assert not invariant_projection_dataframe().empty
    assert event_certificate("cooling_failure", True, severity="warning")["passed"]
    assert not event_certificate_dataframe().empty


def test_residual_aware_decision_bounded_outputs():
    result = run_flowsheet()
    system = build_flowsheet_residual_system(result)
    corrections = correction_certificate_dataframe(system)
    assert not reject_residual_critical_candidate(system)["rejected"]
    assert not corrections["rejected"].astype(bool).any()
    assert abs(system.mass_residuals[0].relative_error_pct) < 1.0e-9
    assert 0.0 <= residual_risk_score(system) <= 1.0
    doe = residual_aware_doe_score({"candidate_id": "h2_pressure", "H2_kg_h": 0.02, "pressure_MPa": 1.8}, system)
    posterior = residual_aware_posterior_weight({"k_h2_transfer": 1.0}, system)
    risk = residual_aware_uncertainty_risk(0.1, system)
    df = residual_aware_decision_dataframe(system)
    assert 0.0 <= doe["residual_aware_score"] <= 1.0
    assert 0.0 <= posterior["posterior_weight"] <= 1.0
    assert 0.0 <= risk["risk_probability"] <= 1.0
    assert not df.empty


def test_evidence_chain_complete_and_actionable():
    chain = build_evidence_chain()
    status = validate_evidence_chain_completeness(chain)
    confidence = evidence_weighted_confidence(chain)
    gaps = evidence_gap_dataframe()
    upgrades = recommend_evidence_upgrade(chain)
    assert not chain.empty
    assert status["rows"] == len(chain)
    assert 0.0 <= confidence["confidence_score"] <= 100.0
    assert {"VLE/flash recovery", "reaction calorimetry", "solution rheology"}.issubset(set(gaps["detail"]))
    assert not upgrades.empty


def test_split_core_helpers_have_real_assertions():
    result = run_flowsheet()
    system = build_flowsheet_residual_system(result)
    row = weighted_data_residual(1.0, 1.1, sigma=0.1, unit="wt%")
    objective = combined_residual_objective([row], system)
    fit = run_fit_with_residual_constraints(result_or_residual_system=system)
    assert row["sse"] > 0
    assert objective["finite"]
    assert fit["accepted"]
    assert not fit_runner_dataframe(result_or_residual_system=system).empty
    assert fit_diagnostics_record(fit)["finite_objective"]
    assert not fit_diagnostics_dataframe(fit).empty
    assert physical_penalty(2.0, 0.0, 1.0) > 0
    assert not physical_penalty_breakdown({"x": 2.0}, {"x": (0.0, 1.0)}).empty
    assert reaction_mass_balance_record(1.0, 1.0)["passed"]
    assert not reaction_balance_dataframe().empty
    assert polymer_moment_estimates(100.0, 200.0)["PDI"] == 2.0
    assert not polymer_moments_dataframe().empty
    assert heat_release_from_conversion(1000.0, 0.5, 95.0)["Q_rxn_kW"] > 0
    assert not heat_release_dataframe().empty
    assert not reactor_residuals_dataframe().empty
    assert material_closure_record(1.0, 1.0)["passed"]
    assert not material_closure_dataframe().empty
    assert energy_closure_record(1.0, 1.0)["passed"]
    assert not energy_closure_dataframe().empty
    assert not unit_residuals_dataframe().empty
    assert project_kpis_with_bounds({"conversion": 2.0})["conversion"] == 1.0
    assert not kpi_projection_dataframe().empty
    assert transport_residuals_dataframe()["passed"].all()
