import json
import math

import numpy as np
import pandas as pd

from epdm_sim.bayesian_doe import (
    CandidateExperiment,
    generate_candidate_design_space,
    rank_bayesian_doe_candidates,
    score_candidate_by_engineering_feasibility,
    score_candidate_by_uncertainty,
)
from epdm_sim.constrained_window import (
    WindowResult,
    constrained_windows_dataframe,
    evaluate_window_robustness,
    generate_feasible_windows,
    recommend_validation_experiments_for_window,
)
from epdm_sim.digital_twin_3d import available_view_modes, equipment_detail_dataframe, equipment_detail_text, selectable_equipment
from epdm_sim.dimensional_checks import DimensionalCheckResult, dimensional_checks_dataframe, mpa_pa_consistency, wt_fraction_consistency
from epdm_sim.fluid_props import (
    FluidPropertyResult,
    PipeHydraulicsResult,
    RheologyModelParameters,
    ViscosityModelParameters,
    calculate_fluid_properties,
    calculate_pipe_hydraulics,
    estimate_stream_volumetric_flow_m3_h,
    load_fluid_property_calibration,
)
from epdm_sim.flowsheet import (
    FlowsheetResult,
    ProcessConfig,
    build_feed_stream,
    build_process_graph,
    calculate_preheat,
    load_default_config,
    normalize_process_config,
    quench_reactor,
    run_flowsheet,
)
from epdm_sim.parameter_estimation import (
    ParameterEstimationResult,
    default_estimation_parameters,
    load_parameter_sets,
    parameter_sets_dataframe,
)
from epdm_sim.posterior import PosteriorResult, log_likelihood_proxy, log_prior_bounds, posterior_summary, run_lightweight_mcmc
from epdm_sim.reactor import DynamicSemibatchODEResult, ReactorResult, ReactorStage, estimate_liquid_volume_flow_L_h, simulate_reactor
from epdm_sim.recipe import Recipe, RecipeStep, default_semibatch_recipe, recipe_from_dict, recipe_from_json, recipe_to_dataframe
from epdm_sim.rheology import (
    RheologyResult,
    apparent_viscosity_from_zero_shear,
    calculate_rheology,
    rheology_models_dataframe,
    zero_shear_solution_viscosity,
)
from epdm_sim.sensitivity import default_values_for_variable, scan_single_variable, scan_two_variables


def test_v5_1_fluid_and_flowsheet_direct_calls_are_physical():
    cfg = load_default_config()
    normalized = normalize_process_config({"reactor_mode": "semi_batch", "U_W_m2K": 250, "A_m2": 1.5})
    assert normalized["reactor_mode"] == "Semi-batch Reactor"
    feed = build_feed_stream(cfg)
    assert feed.total_mass_flow() > 0
    preheated, q_preheat, cp_mix = calculate_preheat(feed, cfg.temperature_C + 273.15)
    assert preheated.temperature_K > feed.temperature_K
    assert q_preheat >= 0
    assert cp_mix > 0
    quenched, quench_info = quench_reactor(preheated, cfg)
    assert quenched.total_mass_flow() >= preheated.total_mass_flow()
    assert quench_info["quench_agent_kg_h"] >= 0
    graph = build_process_graph()
    assert graph.number_of_nodes() > 5

    result = run_flowsheet(cfg)
    assert isinstance(result, FlowsheetResult)
    fluid = calculate_fluid_properties(result.streams["Reactor outlet"], result.kpis["Mw"])
    assert isinstance(fluid, FluidPropertyResult)
    assert fluid.liquid_density_kg_m3 > 0
    assert fluid.dynamic_viscosity_Pa_s > 0
    flow = estimate_stream_volumetric_flow_m3_h(result.streams["Reactor outlet"], fluid.liquid_density_kg_m3)
    hydraulics = calculate_pipe_hydraulics(fluid.liquid_density_kg_m3, fluid.dynamic_viscosity_Pa_s, flow, 10, 0.025, 4.5e-5, 0.65)
    assert isinstance(hydraulics, PipeHydraulicsResult)
    assert hydraulics.pressure_drop_kPa >= 0
    assert load_fluid_property_calibration() is not None
    assert ViscosityModelParameters().A_mu > 0
    assert RheologyModelParameters(model="power-law").power_law_n > 0


def test_v5_1_reactor_recipe_and_rheology_direct_calls_are_bounded():
    cfg = load_default_config()
    feed = build_feed_stream(cfg)
    reactor = simulate_reactor(feed, cfg.temperature_C + 273.15, cfg.pressure_MPa, cfg.residence_time_min, cfg.reactor_volume_L, cfg.catalyst_umol_h, cfg.AlTi_ratio, cfg.BHT_ratio)
    assert isinstance(reactor, ReactorResult)
    assert reactor.polymer_kg_h >= 0
    assert all(0 <= value <= 100 for value in reactor.conversions.values())
    assert isinstance(reactor.stages[0], ReactorStage)
    assert estimate_liquid_volume_flow_L_h(feed) > 0
    dynamic_placeholder = DynamicSemibatchODEResult(pd.DataFrame({"t": [0, 1]}), pd.DataFrame(), {})
    assert len(dynamic_placeholder.time_profile()) == 2

    recipe = default_semibatch_recipe(20)
    assert isinstance(recipe, Recipe)
    assert isinstance(recipe.steps[0], RecipeStep)
    payload = recipe.to_dict()
    assert isinstance(recipe_from_dict(payload), Recipe)
    assert isinstance(recipe_from_json(json.dumps(payload)), Recipe)
    assert not recipe_to_dataframe(recipe).empty

    mu0_low = zero_shear_solution_viscosity(373.15, 5, 300000)
    mu0_high = zero_shear_solution_viscosity(373.15, 20, 300000)
    assert mu0_high > mu0_low
    mu_slow = apparent_viscosity_from_zero_shear(mu0_high, 1.0, "power-law")
    mu_fast = apparent_viscosity_from_zero_shear(mu0_high, 100.0, "power-law")
    assert mu_fast <= mu_slow
    rheo = calculate_rheology(373.15, 12, 350000, 10, rheology_params={"model": "carreau-yasuda"})
    assert isinstance(rheo, RheologyResult)
    assert rheo.apparent_viscosity_Pa_s > 0
    assert not rheology_models_dataframe().empty


def test_v5_1_estimation_posterior_dimensional_direct_calls(tmp_path):
    defaults = default_estimation_parameters()
    assert defaults["k_E_ref"] > 0
    registry = load_parameter_sets()
    assert "active_set_id" in registry
    assert parameter_sets_dataframe() is not None
    residuals = pd.DataFrame({"target": ["Mw"], "observed": [1.0], "predicted": [1.1], "residual": [0.1]})
    per = ParameterEstimationResult(
        "combined",
        "least_squares",
        defaults,
        defaults,
        residuals,
        {"Mw": 0.9},
        {"Mw": 0.1},
        pd.DataFrame([{"split": "train", "MAE": 0.1}]),
        pd.DataFrame([{"parameter": "k_E_ref", "confidence": 0.8}]),
    )
    assert not per.params_dataframe().empty
    assert not per.metrics_dataframe().empty

    assert log_prior_bounds(defaults) == 0.0
    assert math.isfinite(log_likelihood_proxy(defaults))
    posterior = run_lightweight_mcmc(n_steps=12, seed=2)
    assert isinstance(posterior, PosteriorResult)
    assert 0 <= posterior.acceptance_rate <= 1
    summary, ci, corr = posterior_summary(posterior.samples)
    assert not summary.empty and not ci.empty and not corr.empty

    assert mpa_pa_consistency(1.0, 1.0e6)
    assert wt_fraction_consistency(10.0, 0.1)
    dim = DimensionalCheckResult("x", True, "ok", "message")
    assert dim.as_dict()["passed"] is True
    assert not dimensional_checks_dataframe().empty


def test_v5_1_doe_windows_sensitivity_and_3d_direct_calls():
    cfg = ProcessConfig()
    candidates = generate_candidate_design_space("EPDM_EPM_metallocene_solution", cfg)
    assert candidates
    info, rationale = score_candidate_by_uncertainty(candidates[0], {"beta_P": 1.0, "ktr_H2": 1.0})
    assert info >= 0 and rationale
    flags, risk = score_candidate_by_engineering_feasibility(candidates[0])
    assert set(flags) >= {"preflight", "cooling_margin"}
    assert 0 <= risk <= 1
    ranked = rank_bayesian_doe_candidates("EPDM_EPM_metallocene_solution", cfg, {"beta_P": 1.0}, seed=3)
    assert not ranked.empty
    candidate = CandidateExperiment({}, 1.0, 0.5, 0.1, {"preflight": True}, "reason")
    assert candidate.as_dict()["expected_information_gain"] == 1.0

    windows = generate_feasible_windows(cfg)
    assert windows
    first = windows[0]
    assert isinstance(first, WindowResult)
    assert 0 <= evaluate_window_robustness(first) <= 100
    assert recommend_validation_experiments_for_window(first)
    assert not constrained_windows_dataframe(windows).empty

    vals = default_values_for_variable(cfg, "temperature_C", points=3)
    assert len(vals) == 3
    scan = scan_single_variable(cfg, "hydrogen", [1.0, 5.0])
    assert len(scan) == 2
    scan2 = scan_two_variables(cfg, "temperature_C", [95.0], "pressure_MPa", [0.8, 1.0])
    assert len(scan2) == 2

    assert available_view_modes()
    assert selectable_equipment()
    assert not equipment_detail_dataframe(run_flowsheet(cfg)).empty
    assert equipment_detail_text("Reactor1", run_flowsheet(cfg))["设备"] == "Reactor1"
