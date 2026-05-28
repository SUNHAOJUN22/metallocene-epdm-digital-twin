import pandas as pd

from epdm_sim.profile_alignment import align_model_to_experiment, calculate_profile_residuals, profile_fit_score


def test_profile_alignment_and_score():
    model = pd.DataFrame({"time_min": [0, 10], "T_C": [90, 100], "Q_rxn_kW": [0, 2]})
    exp = pd.DataFrame({"time_min": [0, 5, 10], "T_C": [90, 96, 101], "Q_rxn_kW": [0, 1, 2]})
    aligned = align_model_to_experiment(model, exp)
    residuals = calculate_profile_residuals(aligned)
    score = profile_fit_score(residuals)
    assert "residual_T_C" in residuals.columns
    assert set(score["metric"]) == {"T_C", "Q_rxn_kW"}
    assert score["rmse"].ge(0).all()
