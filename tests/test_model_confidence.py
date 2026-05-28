from epdm_sim.conservation import ConservationResult
from epdm_sim.flowsheet import load_default_config, run_flowsheet
from epdm_sim.model_confidence import build_model_confidence_card


def test_model_confidence_card_range():
    result = run_flowsheet(load_default_config())
    card = build_model_confidence_card(result)
    assert 0.0 <= card.overall_score <= 100.0
    assert not card.as_dataframe().empty


def test_failed_conservation_lowers_numerical_score():
    failed = ConservationResult(
        "bad_balance",
        100.0,
        50.0,
        50.0,
        50.0,
        1.0,
        False,
        "error",
        "bad",
        "fix",
    )
    card = build_model_confidence_card(conservation_results=[failed])
    assert card.numerical_score < 100.0
    assert any("守恒" in flag for flag in card.risk_flags)


def test_default_parameter_source_recommends_more_data():
    card = build_model_confidence_card(parameter_set_source="default")
    assert card.calibration_score < 90.0
    assert card.recommended_next_data


def test_model_confidence_includes_v4_4_breakdown_scores():
    card = build_model_confidence_card()
    assert 0.0 <= card.preflight_score <= 100.0
    assert 0.0 <= card.conservation_score <= 100.0
    assert 0.0 <= card.engineering_rule_score <= 100.0
    assert 0.0 <= card.identifiability_score <= 100.0
    assert 0.0 <= card.uncertainty_score <= 100.0
