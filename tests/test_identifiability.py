import pandas as pd

from epdm_sim.identifiability import evaluate_identifiability, finite_difference_sensitivity


def test_sensitivity_matrix_and_condition_number_finite():
    sensitivity = finite_difference_sensitivity()
    assert not sensitivity.empty
    result = evaluate_identifiability()
    assert result.condition_number == result.condition_number
    assert not result.parameter_correlation.empty


def test_missing_pressure_variation_flags_beta_p_weak():
    data = pd.DataFrame({"pressure_MPa": [1.0, 1.0, 1.0], "hydrogen_feed": [1, 2, 3], "residence_time_min": [20, 30, 40], "ethylene_feed": [1, 2, 3], "enb_feed": [1, 1.5, 2]})
    result = evaluate_identifiability(data)
    row = result.status[result.status["parameter"] == "beta_P"].iloc[0]
    assert row["status"] == "weakly_identifiable"


def test_missing_h2_variation_flags_ktr_h2_weak():
    data = pd.DataFrame({"pressure_MPa": [0.7, 1.0, 2.0], "hydrogen_feed": [1, 1, 1], "residence_time_min": [20, 30, 40], "ethylene_feed": [1, 2, 3], "enb_feed": [1, 1.5, 2]})
    result = evaluate_identifiability(data)
    row = result.status[result.status["parameter"] == "ktr_H2"].iloc[0]
    assert row["status"] == "weakly_identifiable"
