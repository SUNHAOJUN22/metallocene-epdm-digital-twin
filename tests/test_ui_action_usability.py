from epdm_sim.ui_workflow import UIAction, load_ui_actions, ui_registry_usability_dataframe


def test_ui_action_registry_has_no_redundant_user_facing_entries():
    df = ui_registry_usability_dataframe()
    assert not df.empty
    assert df["passed"].all()


def test_ui_action_registry_detects_duplicate_signature():
    actions = load_ui_actions()
    duplicate = UIAction(
        action_id="duplicate_fast_flowsheet",
        label="重复快速流程模拟",
        page=actions[0].page,
        trigger_type=actions[0].trigger_type,
        target_task=actions[0].target_task,
        dependencies=list(actions[0].dependencies),
        expected_runtime_s=actions[0].expected_runtime_s,
        invalidates=list(actions[0].invalidates),
        reads=list(actions[0].reads),
        writes=list(actions[0].writes),
        user_feedback="重复入口用于测试冗余检测。",
    )
    df = ui_registry_usability_dataframe([*actions, duplicate])
    row = df[df["rule"] == "no_duplicate_action_signature"].iloc[0]
    assert bool(row["passed"]) is False
