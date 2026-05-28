from epdm_sim.flowsheet import run_flowsheet
from epdm_sim.report import export_excel
from epdm_sim.report_consistency import (
    check_excel_required_sheets,
    check_export_does_not_run_heavy,
    compare_report_manifest_metadata,
    excel_sheet_names,
    read_excel_metadata,
    report_consistency_dataframe,
)


def test_report_consistency_checks_required_metadata_and_sheets():
    excel = export_excel(run_flowsheet())
    sheets = excel_sheet_names(excel)
    assert "validity_envelope" in sheets
    assert "report_consistency" in sheets
    assert "calibration_scores" in sheets
    assert all(len(name) <= 31 for name in sheets)
    assert "dyn_resid_feedback_status" in sheets
    assert check_excel_required_sheets(excel)[0].passed
    metadata = read_excel_metadata(excel)
    assert metadata["software_version"].startswith("V")
    checks = compare_report_manifest_metadata(excel)
    assert checks
    assert check_export_does_not_run_heavy({"dynamic_ode": {"status": "not_run"}})[0].passed
    df = report_consistency_dataframe(excel, task_status={"dynamic_ode": {"status": "not_run"}})
    assert not df.empty
    assert not (df["severity"] == "error").any()
