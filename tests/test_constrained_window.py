from epdm_sim.constrained_window import generate_feasible_windows, rank_process_windows


def test_constrained_windows_are_feasible():
    windows = rank_process_windows(generate_feasible_windows())
    assert windows
    for window in windows:
        assert 0.0 <= window.robustness_score <= 100.0
        assert all(value >= 0 for value in window.constraint_margins.values())

