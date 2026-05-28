from epdm_sim.flowsheet import run_flowsheet
from epdm_sim.model_audit_report import build_model_audit_report


def test_model_audit_report_finite_and_bounded():
    result = run_flowsheet()
    audit = build_model_audit_report(result)
    card = audit.model_confidence_card
    assert 0.0 <= card.overall_score <= 100.0
    assert not audit.preflight_summary.empty
    assert not audit.conservation_summary.empty
    assert not audit.top_risks.empty
    assert not audit.recommended_next_actions.empty


def test_missing_calibration_lowers_calibration_score():
    result = run_flowsheet()
    default_audit = build_model_audit_report(result, parameter_set_source="default")
    calibrated_audit = build_model_audit_report(result, parameter_set_source="user_calibrated", calibration_metrics={"mae": 1.0})
    assert default_audit.model_confidence_card.calibration_score < calibrated_audit.model_confidence_card.calibration_score
