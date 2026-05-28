from epdm_sim.workflow_wizard import load_workflow_steps, next_recommended_action, workflow_status
from epdm_sim.pages.workflow_wizard_page import render_page


def test_workflow_wizard_steps_are_manual_for_heavy_tasks():
    steps = load_workflow_steps()
    assert steps
    assert all(step.heavy for step in steps if step.target_action in {"run_parameter_estimation", "run_uncertainty", "run_bayesian_doe", "run_pareto", "run_dynamic_template_ode"})
    assert next_recommended_action({}) == "load_case"
    assert not workflow_status({}).empty
    assert callable(render_page)

