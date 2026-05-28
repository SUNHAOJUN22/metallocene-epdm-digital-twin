import pandas as pd

from epdm_sim.calibration_loop import (
    estimate_information_gain,
    recommend_experiments_for_weak_parameters,
    run_calibration_loop,
)


def test_weak_beta_p_recommends_pressure_gradient():
    df = recommend_experiments_for_weak_parameters(["beta_P"])
    assert not df.empty
    assert df["pressure_MPa"].dropna().nunique() >= 3


def test_weak_ktr_h2_recommends_hydrogen_gradient():
    df = recommend_experiments_for_weak_parameters(["ktr_H2"])
    assert "hydrogen_g_h" in df
    assert df["hydrogen_g_h"].dropna().nunique() >= 2


def test_information_gain_finite():
    candidates = recommend_experiments_for_weak_parameters(["beta_P", "ktr_H2"])
    gain = estimate_information_gain(candidates, ["beta_P", "ktr_H2"])
    assert not gain.empty
    assert gain["expected_information_gain"].between(0, 100).all()


def test_calibration_loop_outputs_finite_recommendations_without_heavy_models():
    dataset = pd.DataFrame({"pressure_MPa": [1.0], "hydrogen_feed": [5.0], "residence_time_min": [30.0]})
    result = run_calibration_loop(dataset=dataset)
    assert not result.identifiability_summary.empty
    assert not result.recommended_experiments.empty
    assert not result.expected_information_gain.empty
    assert result.current_parameter_set
