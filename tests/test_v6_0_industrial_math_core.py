import numpy as np

from epdm_sim.dynamic_core.dae_constraints import dae_constraints_dataframe, dae_constraints_status
from epdm_sim.dynamic_core.state_invariants import state_invariants_dataframe, state_invariants_status
from epdm_sim.dynamic_template_reactor import simulate_template_semibatch_ode
from epdm_sim.flowsheet import load_default_config, run_flowsheet
from epdm_sim.math_core.balance_laws import accumulation_identity, balance_law_acceptance, balance_law_records
from epdm_sim.math_core.dimension_signatures import dimension_signature_dataframe, validate_dimension_signatures
from epdm_sim.math_core.equation_graph import equation_graph_acceptance, equation_graph_dataframe
from epdm_sim.math_core.kinetic_identities import arrhenius_rate_ratio, eyring_rate_constant, kinetic_identity_checks_dataframe
from epdm_sim.math_core.model_confidence import combine_confidence_components, model_confidence_kernel_dataframe
from epdm_sim.math_core.residual_graph import residual_graph_acceptance, residual_graph_dataframe
from epdm_sim.math_core.thermodynamic_identities import (
    delta_g_from_equilibrium_constant,
    equilibrium_constant_from_delta_g,
    gibbs_from_enthalpy_entropy,
    thermodynamic_identity_checks_dataframe,
)
from epdm_sim.model_confidence_engine import (
    confidence_decomposition,
    model_confidence_engine_dataframe,
    model_confidence_score,
    recommend_high_value_validation_data,
)
from epdm_sim.model_graph import (
    build_equation_graph,
    link_benchmark_to_dataset,
    link_equation_to_residual,
    link_residual_to_benchmark,
    model_traceability_dataframe,
    model_traceability_summary,
)
from epdm_sim.data_lineage_graph import build_data_lineage_graph, data_lineage_graph_summary
from epdm_sim.property_model_selector import apply_selected_property_model, property_model_selection_dataframe, property_model_selector
from epdm_sim.residual_graph import build_residual_graph, residual_traceability_summary
from epdm_sim.residual_system import build_flowsheet_residual_system
from epdm_sim.solver_core.constrained_solver import (
    ConstrainedSolveResult,
    constrained_solver_dataframe,
    minimize_residual_subject_to_bounds,
    solve_with_mass_energy_constraints,
)
from epdm_sim.solver_core.dae_solver import dae_solver_dataframe, dae_solver_status
from epdm_sim.solver_core.residual_minimizer import enforce_heat_balance_constraints, enforce_phase_split_constraints, residual_minimizer_dataframe
from epdm_sim.solver_core.solver_certificates import generate_solver_certificate, solver_certificate_dataframe
from epdm_sim.solver_core.stability_region import stability_region_dataframe, stability_region_record
from epdm_sim.validation_evidence import evidence_weight, validation_evidence_dataframe


def test_v6_balance_thermo_kinetic_and_dimension_identities():
    result = run_flowsheet(load_default_config())
    residual_system = build_flowsheet_residual_system(result)

    identity = accumulation_identity(2.0, 5.0, 1.0, generation_rate=0.0, consumption_rate=2.0)
    assert identity["passed"]
    assert not balance_law_records(residual_system).empty
    assert balance_law_acceptance(residual_system)["passed"]

    dg = gibbs_from_enthalpy_entropy(-50000.0, 373.15, -100.0)
    K = equilibrium_constant_from_delta_g(dg, 373.15)
    assert np.isfinite(delta_g_from_equilibrium_constant(K, 373.15))
    assert thermodynamic_identity_checks_dataframe()["passed"].all()

    assert arrhenius_rate_ratio(45000.0, 390.0, 350.0) > 1.0
    assert eyring_rate_constant(75000.0, 373.15) > 0.0
    assert kinetic_identity_checks_dataframe()["passed"].all()

    assert validate_dimension_signatures()["passed"]
    assert dimension_signature_dataframe()["passed"].all()
    assert 0.0 <= combine_confidence_components({"a": 80.0, "b": 100.0}) <= 100.0
    assert model_confidence_kernel_dataframe()["passed"].all()


def test_v6_graphs_trace_equations_residuals_and_lineage():
    result = run_flowsheet(load_default_config())
    residual_system = build_flowsheet_residual_system(result)

    assert equation_graph_acceptance()["passed"]
    assert not equation_graph_dataframe().empty
    assert residual_graph_acceptance(residual_system)["passed"]
    assert not residual_graph_dataframe(residual_system).empty

    equation_edges = build_equation_graph()
    assert not equation_edges.empty
    assert link_equation_to_residual("reaction_heat_release")["passed"]
    linked = link_residual_to_benchmark("heat_release_proxy")
    assert not linked.empty
    assert link_benchmark_to_dataset(str(linked.iloc[0]["benchmark_id"]))["passed"]

    traceability = model_traceability_dataframe()
    assert not traceability.empty
    assert model_traceability_summary()["passed"]
    assert build_data_lineage_graph()["passed"].all()
    assert data_lineage_graph_summary()["passed"]
    assert not build_residual_graph(residual_system).empty
    assert residual_traceability_summary(residual_system)["passed"]


def test_v6_constrained_solver_certificates_and_dae_invariants():
    result = run_flowsheet(load_default_config())
    residual_system = build_flowsheet_residual_system(result)
    dynamic = simulate_template_semibatch_ode(total_time_min=4.0, dt_min=2.0, solver_mode="explicit_bounded")

    projected = minimize_residual_subject_to_bounds(12.0, 0.0, 10.0)
    assert projected["projected"] == 10.0
    phase = enforce_phase_split_constraints(100.0, 10.0, 90.0)
    heat = enforce_heat_balance_constraints(5.0, 5.0)
    assert phase["accepted"] and heat["accepted"]
    assert not residual_minimizer_dataframe(residual_system).empty

    solve_result = solve_with_mass_energy_constraints(residual_system)
    assert isinstance(solve_result, ConstrainedSolveResult)
    assert solve_result.accepted
    assert constrained_solver_dataframe(residual_system)["accepted"].iloc[0]
    assert generate_solver_certificate(residual_system)["solver_certificate_passed"]
    assert solver_certificate_dataframe(residual_system)["solver_certificate_passed"].iloc[0]

    assert dae_constraints_status(dynamic)["passed"]
    assert not dae_constraints_dataframe(dynamic).empty
    assert state_invariants_status(dynamic)["passed"]
    assert not state_invariants_dataframe(dynamic).empty
    assert dae_solver_status(dynamic)["dae_ready"]
    assert not dae_solver_dataframe(dynamic).empty
    assert stability_region_record(dynamic)["passed"]
    assert stability_region_dataframe(dynamic)["passed"].iloc[0]


def test_v6_evidence_confidence_and_property_selector():
    result = run_flowsheet(load_default_config())
    residual_system = build_flowsheet_residual_system(result)

    assert evidence_weight("plant") > evidence_weight("experiment") > evidence_weight("synthetic") > evidence_weight("regression_snapshot")
    evidence = validation_evidence_dataframe()
    assert not evidence.empty
    assert evidence["evidence_weight"].between(0, 1).all()

    score = model_confidence_score(residual_system=residual_system, model_outputs=result.kpis)
    assert score["passed"]
    assert 0.0 <= score["overall_score"] <= 100.0
    assert not confidence_decomposition(residual_system=residual_system, model_outputs=result.kpis).empty
    assert not model_confidence_engine_dataframe(residual_system=residual_system, model_outputs=result.kpis).empty
    assert recommend_high_value_validation_data()["recommended_action"].astype(str).str.len().gt(0).all()

    selected = property_model_selector(parameter_type="viscosity", conditions={"temperature_C": 100.0})
    assert 0.0 <= selected["confidence_score"] <= 100.0
    applied = apply_selected_property_model(2.0, "viscosity_multiplier", parameter_type="viscosity", conditions={"temperature_C": 100.0})
    assert applied["passed"]
    selection = property_model_selection_dataframe(conditions={"temperature_C": 100.0})
    assert not selection.empty
    assert selection["confidence_score"].between(0, 100).all()
