from epdm_sim.ui_workflow import load_ui_actions
from scripts.ui_e2e_smoke import run_ui_e2e_smoke


def test_ui_e2e_static_contract_does_not_map_exports_to_heavy_tasks():
    actions = load_ui_actions()
    assert actions
    assert all(action.target_task for action in actions if action.trigger_type == "button_manual")
    assert not [
        action.action_id
        for action in actions
        if action.trigger_type == "export" and any(token in (action.target_task or "") for token in ("ode", "cfd", "optimization", "posterior", "doe"))
    ]


def test_ui_e2e_smoke_http_contract_if_server_running():
    result = run_ui_e2e_smoke()
    if result["http_available"]:
        assert result["status"] == 200
    else:
        assert result["status"] == 0
        assert result["http_error"]
    assert result["passed"]
