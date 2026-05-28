from scripts.ui_e2e_workflow import run_ui_e2e_workflow


def test_ui_e2e_workflow_contract_is_non_destructive():
    result = run_ui_e2e_workflow(timeout_s=1.0)
    assert result["passed"] is True
    assert not result["heavy_manual_without_task"]
    assert not result["ui_audit_errors"]
    assert result["has_workflow_page"] is True
