from epdm_sim.property_confidence import get_property_confidence, property_confidence_dataframe, propagate_property_uncertainty_to_model_confidence


def test_property_confidence_loads_and_scores():
    df = property_confidence_dataframe()
    assert not df.empty
    eth = get_property_confidence("ethylene", "MW")
    assert eth["confidence_level"] == "high"
    score = propagate_property_uncertainty_to_model_confidence()
    assert 0 <= score["property_confidence_score"] <= 100
