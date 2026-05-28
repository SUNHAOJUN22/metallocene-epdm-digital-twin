"""R&D workflow wizard metadata and next-action guidance."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class WorkflowStep:
    """One workflow wizard step."""

    step_id: str
    label: str
    required_inputs: list[str]
    target_action: str
    expected_runtime_s: float
    heavy: bool = False
    dependencies: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "label": self.label,
            "required_inputs": ", ".join(self.required_inputs),
            "target_action": self.target_action,
            "expected_runtime_s": self.expected_runtime_s,
            "heavy": self.heavy,
            "dependencies": ", ".join(self.dependencies),
        }


def load_workflow_steps() -> list[WorkflowStep]:
    """Return the V4.7 R&D workflow steps."""
    return [
        WorkflowStep("select_template_case", "选择模板和案例", ["template_id", "case"], "load_case", 0.2),
        WorkflowStep("run_fast_flowsheet", "运行快速流程", ["SimulationState"], "run_fast_flowsheet", 0.5, False, ["select_template_case"]),
        WorkflowStep("run_checks", "运行preflight/守恒/趋势检查", ["flowsheet_result"], "run_conservation_checks", 0.5, False, ["run_fast_flowsheet"]),
        WorkflowStep("import_experiments", "导入实验数据", ["CSV/Excel"], "experiment_data_import", 0.5),
        WorkflowStep("fit_parameters", "参数估计或后验", ["experiment_data"], "run_parameter_estimation", 8.0, True, ["import_experiments"]),
        WorkflowStep("run_uncertainty", "不确定性分析", ["flowsheet_result", "parameter_uncertainty"], "run_uncertainty", 5.0, True, ["fit_parameters"]),
        WorkflowStep("run_bayesian_doe", "Bayesian DOE", ["uncertainty_result"], "run_bayesian_doe", 5.0, True, ["run_uncertainty"]),
        WorkflowStep("optimize_window", "工程约束窗口优化", ["target_grade", "constraints"], "run_pareto", 8.0, True, ["run_fast_flowsheet"]),
        WorkflowStep("dynamic_cfd_review", "动态ODE或CFD复核", ["candidate_window"], "run_dynamic_template_ode", 4.0, True, ["optimize_window"]),
        WorkflowStep("export_report_package", "导出报告和复现实验包", ["existing_results"], "export_repro_package", 2.0, False, ["run_fast_flowsheet"]),
    ]


def workflow_status(available_results: dict[str, Any] | None = None) -> pd.DataFrame:
    """Return wizard step status without running heavy tasks."""
    available_results = available_results or {}
    rows = []
    for step in load_workflow_steps():
        complete = bool(available_results.get(step.step_id) or available_results.get(step.target_action))
        stale_reason = "" if complete else "waiting for inputs or manual action"
        rows.append({**step.as_dict(), "status": "complete" if complete else "pending", "stale_reason": stale_reason, "cached": False})
    return pd.DataFrame(rows)


def next_recommended_action(available_results: dict[str, Any] | None = None) -> str:
    """Return the next unfinished workflow action id."""
    status = workflow_status(available_results)
    pending = status[status["status"] != "complete"]
    return str(pending.iloc[0]["target_action"]) if not pending.empty else "export_repro_package"

