from epdm_sim.flowsheet import run_flowsheet
from epdm_sim.model_audit_report import build_model_audit_report


def test_model_audit_includes_calibration_score_breakdown():
    result = run_flowsheet()
    audit = build_model_audit_report(
        result,
        calibration_metrics={"fit_R2": 0.8},
        property_calibration_metrics={"RMSE": 0.02},
        thermo_calibration_metrics={"RMSE": 0.01},
        parameter_set_source="calibrated",
        data_quality={"complete_rows": 10},
    )
    row = audit.calibration_summary.iloc[0].to_dict()
    assert row["kinetic_calibration_score"] >= 35
    assert row["property_calibration_score"] >= 35
    assert row["thermo_calibration_score"] >= 35
    assert row["validation_data_score"] >= 35
