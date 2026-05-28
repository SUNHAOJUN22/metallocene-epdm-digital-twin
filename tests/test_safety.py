from epdm_sim.flowsheet import load_default_config, run_flowsheet
from epdm_sim.safety import calculate_safety


def test_safety_result_is_finite_and_ranked():
    result = run_flowsheet(load_default_config())
    safety = calculate_safety(result)
    assert safety.runaway_risk_level in {"low", "medium", "high"}
    assert safety.MTSR_like_C > 0
    assert not safety.as_dataframe().empty
