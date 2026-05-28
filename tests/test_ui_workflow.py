from epdm_sim.ui_workflow import get_ui_action, load_ui_actions, ui_actions_dataframe


def test_button_manual_actions_have_target_tasks():
    actions = load_ui_actions()
    manual = [action for action in actions if action.trigger_type == "button_manual"]
    assert manual
    assert all(action.target_task for action in manual)


def test_export_actions_do_not_auto_trigger_models():
    exports = [action for action in load_ui_actions() if action.trigger_type == "export"]
    assert exports
    assert all(action.trigger_type != "auto_cached" for action in exports)
    assert all(action.target_task for action in exports)


def test_actions_declare_reads_writes_and_dataframe():
    for action in load_ui_actions():
        assert action.reads
        assert action.writes
    assert get_ui_action("run_cfd").target_task == "cfd"
    assert not ui_actions_dataframe().empty
