import app

from epdm_sim.flowsheet import run_flowsheet
from epdm_sim.governance_certificate import governance_certificate_dataframe, governance_certificate_gate, governance_certificate_summary
from epdm_sim.pages.model_governance_page import render_model_governance_page
from epdm_sim.ui_audit import run_ui_audit


def test_model_governance_page_registered_and_certificate_available():
    result = run_flowsheet()
    df = governance_certificate_dataframe(result)
    summary = governance_certificate_summary(result)
    gate = governance_certificate_gate(result)
    errors = [issue for issue in run_ui_audit() if issue.severity == "error"]
    assert "模型治理与可信度证书" in app.PAGES
    assert callable(render_model_governance_page)
    assert not df.empty
    assert summary["rows"] == len(df)
    assert gate["passed"]
    assert not errors

