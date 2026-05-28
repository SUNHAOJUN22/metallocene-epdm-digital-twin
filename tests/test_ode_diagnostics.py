from epdm_sim.dynamic_template_reactor import simulate_template_semibatch_ode
from epdm_sim.ode_diagnostics import ODEDiagnostic, diagnose_dynamic_ode, ode_diagnostics_dataframe, rhs_term_schema_dataframe


def test_ode_diagnostics_for_bdf_or_fallback():
    result = simulate_template_semibatch_ode(total_time_min=4.0, dt_min=2.0, solver_mode="solve_ivp_bdf")
    diagnostics = diagnose_dynamic_ode(result)
    assert diagnostics
    assert isinstance(diagnostics[0], ODEDiagnostic)
    df = ode_diagnostics_dataframe(result)
    assert not df.empty
    assert df[df["severity"] == "error"].empty
    assert df["diagnostic_id"].str.contains("finite_states").any()


def test_rhs_term_schema_documents_physical_terms():
    schema = rhs_term_schema_dataframe()
    assert {"feed", "reaction_consumption", "heat_generation", "quench"}.issubset(set(schema["term"]))
    assert schema["unit"].astype(str).str.len().gt(0).all()
