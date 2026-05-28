from epdm_sim.doe_optimal import recommend_optimal_doe


def test_doe_returns_feasible_finite_experiments():
    result = recommend_optimal_doe(max_experiments=5)
    assert not result.recommendations.empty
    assert (result.recommendations["cooling_margin_kW"] > 0).all()
    assert (result.recommendations["fouling_index"] < 3).all()
    assert result.recommendations[["temperature_C", "pressure_MPa", "enb_kg_h"]].notna().all().all()
