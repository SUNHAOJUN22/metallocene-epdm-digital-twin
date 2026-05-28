import math

from epdm_sim.flowsheet import load_default_config
from epdm_sim.uncertainty import run_uncertainty_analysis


def test_uncertainty_reproducible_and_finite():
    cfg = load_default_config()
    a = run_uncertainty_analysis(cfg, n_samples=8, seed=11)
    b = run_uncertainty_analysis(cfg, n_samples=8, seed=11)
    assert not a.confidence_intervals.empty
    assert a.confidence_intervals["mean"].map(math.isfinite).all()
    assert a.samples["ENB_wt"].round(8).tolist() == b.samples["ENB_wt"].round(8).tolist()


def test_uncertainty_risk_probabilities_between_zero_and_one():
    result = run_uncertainty_analysis(load_default_config(), n_samples=8, seed=3)
    assert all(0.0 <= value <= 1.0 for value in result.risk_probabilities.values())

