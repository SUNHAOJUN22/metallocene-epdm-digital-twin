from epdm_sim.flowsheet import load_default_config
from epdm_sim.pareto import generate_pareto_windows


def test_pareto_returns_feasible_table():
    result = generate_pareto_windows(load_default_config(), n_samples=10, seed=3)
    assert not result.frontier.empty
    assert {"cooling_margin_kW", "fouling_index", "pipe_pressure_drop_kPa"}.issubset(result.frontier.columns)
    assert (result.frontier["cooling_margin_kW"] > 0).all()


def test_pareto_recommendations_have_labels():
    result = generate_pareto_windows(load_default_config(), n_samples=10, seed=4)
    assert {"稳健窗口", "高ENB窗口", "低风险窗口"}.issubset(set(result.recommended["window"]))
