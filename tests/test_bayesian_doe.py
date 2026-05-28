from epdm_sim.bayesian_doe import recommend_next_experiment_batch, score_candidate_by_uncertainty
from epdm_sim.flowsheet import load_default_config


def test_bayesian_doe_returns_finite_feasible_candidates():
    cfg = load_default_config()
    df = recommend_next_experiment_batch(cfg, {"beta_P": 0.8, "ktr_H2": 0.8}, n=4, seed=3)
    assert not df.empty
    assert df["expected_information_gain"].notna().all()
    assert df.filter(like="feasible_").all().all()


def test_weak_beta_p_scores_pressure_gradient():
    cfg = load_default_config()
    low = cfg.model_copy(deep=True); low.pressure_MPa = 0.7
    base = cfg.model_copy(deep=True); base.pressure_MPa = 1.0
    low_score, _ = score_candidate_by_uncertainty(low, {"beta_P": 1.0})
    base_score, _ = score_candidate_by_uncertainty(base, {"beta_P": 1.0})
    assert low_score >= base_score
