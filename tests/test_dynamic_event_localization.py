from epdm_sim.dynamic_core.event_localization import (
    event_localization_dataframe,
    event_localization_gate,
    event_localization_summary,
    localize_dynamic_events,
)
from epdm_sim.dynamic_template_reactor import simulate_template_semibatch_ode


def test_event_localization_rows_are_bounded():
    dynamic = simulate_template_semibatch_ode(solver_mode="explicit_bounded", total_time_min=4.0, dt_min=0.5)
    rows = localize_dynamic_events(dynamic)
    df = event_localization_dataframe(dynamic)
    summary = event_localization_summary(dynamic)
    gate = event_localization_gate(dynamic)
    assert rows
    assert not df.empty
    assert (df["t_max"] >= df["t_min"]).all()
    assert summary["passed"]
    assert gate["passed"]

