from dataclasses import replace

from epdm_sim.dynamic_template_reactor import simulate_template_semibatch_ode
from epdm_sim.flowsheet import load_default_config, run_flowsheet
from epdm_sim.residual_system import (
    Residual,
    ResidualSystem,
    build_dynamic_residual_system,
    build_flowsheet_residual_system,
    make_residual,
    residual_system_dataframe,
    score_residuals,
)


def test_flowsheet_residual_system_default_passes_or_warns():
    system = build_flowsheet_residual_system(run_flowsheet(load_default_config()))
    df = residual_system_dataframe(system)
    assert isinstance(system, ResidualSystem)
    assert not df.empty
    assert system.overall_score >= 70.0
    assert df["absolute_error"].ge(0).all()


def test_residual_failure_identifies_source():
    residual = make_residual("polymer_vapor", "polymer vapor = 0", 1.0, 0.0, "kg/h", 1e-12, "flash", "keep polymer liquid", "error")
    assert isinstance(residual, Residual)
    assert not residual.passed
    assert residual.suspected_source == "flash"
    assert score_residuals([residual]) < 100.0


def test_dynamic_residual_system_finite():
    dynamic = simulate_template_semibatch_ode(total_time_min=4.0, dt_min=2.0)
    system = build_dynamic_residual_system(dynamic)
    df = system.as_dataframe()
    assert not df.empty
    assert system.overall_score >= 90.0
    assert df["relative_error_pct"].ge(0).all()


def test_residual_system_dataframe_empty_shape():
    empty = residual_system_dataframe(ResidualSystem())
    assert "residual_id" in empty.columns
