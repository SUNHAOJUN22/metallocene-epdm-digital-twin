"""UI action registry for explicit, efficient task triggering."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class UIAction:
    """A user-facing action and its computational side effects."""

    action_id: str
    label: str
    page: str
    trigger_type: str
    target_task: str
    dependencies: list[str] = field(default_factory=list)
    expected_runtime_s: float = 0.0
    invalidates: list[str] = field(default_factory=list)
    reads: list[str] = field(default_factory=list)
    writes: list[str] = field(default_factory=list)
    user_feedback: str = ""

    def as_dict(self) -> dict[str, Any]:
        """Return a flattened action row."""
        return {
            "action_id": self.action_id,
            "label": self.label,
            "page": self.page,
            "trigger_type": self.trigger_type,
            "target_task": self.target_task,
            "dependencies": ", ".join(self.dependencies),
            "expected_runtime_s": self.expected_runtime_s,
            "invalidates": ", ".join(self.invalidates),
            "reads": ", ".join(self.reads),
            "writes": ", ".join(self.writes),
            "user_feedback": self.user_feedback,
        }


def load_ui_actions() -> list[UIAction]:
    """Return the built-in UI action registry."""
    return [
        UIAction(
            "run_fast_flowsheet",
            "运行快速流程模拟",
            "dashboard/sidebar",
            "auto_cached",
            "flowsheet_fast",
            expected_runtime_s=0.5,
            invalidates=["kpis", "engineering_checks", "conservation"],
            reads=["SimulationState", "parameter_set"],
            writes=["flowsheet_result", "kpis"],
            user_feedback="刷新快速流程、热量、流体和产品KPI缓存。",
        ),
        UIAction("run_dynamic_ode", "运行ODE详细釜式模型", "dynamic_reactor_page", "button_manual", "dynamic_ode", ["flowsheet_fast"], 3.0, ["dynamic_profile"], ["SimulationState", "recipe"], ["dynamic_result"], "只运行动态ODE，不触发CFD或优化。"),
        UIAction("run_dynamic_template_ode", "运行模板化动态反应器", "dynamic_reactor_page", "button_manual", "dynamic_template_ode", ["flowsheet_fast"], 3.0, ["dynamic_template_profile"], ["SimulationState", "reaction_template", "recipe"], ["dynamic_template_result"], "按reaction template运行通用状态向量，不触发CFD或优化。"),
        UIAction("run_cfd", "运行CFD有限元可视化", "cfd_page", "button_manual", "cfd", ["flowsheet_fast"], 4.0, ["cfd_metrics"], ["flowsheet_result", "cfd_inputs"], ["cfd_result"], "只运行简化CFD并缓存场数据。"),
        UIAction("run_sensitivity", "运行敏感性分析", "sensitivity_optimization_page", "button_manual", "optimization", ["flowsheet_fast"], 4.0, ["sensitivity_results"], ["SimulationState"], ["sensitivity_result"], "扫描变量，页面切换不自动运行。"),
        UIAction("run_optimizer", "运行单目标优化", "sensitivity_optimization_page", "button_manual", "optimization", ["flowsheet_fast"], 6.0, ["optimization_result"], ["target_grade", "SimulationState"], ["optimization_result"], "按目标牌号反推工艺窗口。"),
        UIAction("run_pareto", "运行Pareto多目标窗口", "sensitivity_optimization_page", "button_manual", "optimization", ["flowsheet_fast"], 8.0, ["pareto_result"], ["constraints", "SimulationState"], ["pareto_result"], "生成多目标可行工艺窗口。"),
        UIAction("run_parameter_estimation", "运行参数估计", "calibration_page", "button_manual", "parameter_estimation", ["experiment_data"], 8.0, ["parameter_estimation"], ["experiment_dataset", "parameter_bounds"], ["parameter_estimation_result"], "拟合失败不覆盖默认参数集。"),
        UIAction("run_posterior_sampling", "运行轻量后验采样", "calibration_page", "button_manual", "posterior_sampling", ["experiment_data"], 8.0, ["posterior_result"], ["experiment_dataset", "parameter_set"], ["posterior_result"], "研发级MCMC手动触发，不覆盖默认参数集。"),
        UIAction("run_calibration_loop", "运行校准-不确定性-DOE闭环", "calibration_page", "button_manual", "calibration_loop", ["experiment_data", "flowsheet_fast"], 6.0, ["calibration_loop"], ["experiment_dataset", "parameter_set", "SimulationState"], ["calibration_loop_result"], "只运行轻量闭环诊断，不触发ODE/CFD/优化。"),
        UIAction("run_time_series_fit", "运行时间序列校准", "calibration_page", "button_manual", "time_series_fit", ["experiment_time_series", "dynamic_template_ode"], 4.0, ["profile_residuals"], ["time_series_dataset", "dynamic_profile"], ["profile_fit_result"], "只对齐已有动态结果和实验时间序列。"),
        UIAction("run_uncertainty", "运行不确定性分析", "heat_fluid_page/report_page", "button_manual", "uncertainty", ["flowsheet_fast"], 5.0, ["uncertainty"], ["SimulationState", "uncertain_parameters"], ["uncertainty_result"], "Monte Carlo/LHS必须手动触发。"),
        UIAction("run_bayesian_doe", "运行不确定性驱动DOE", "calibration_page", "button_manual", "bayesian_doe", ["flowsheet_fast", "uncertainty"], 5.0, ["bayesian_doe"], ["SimulationState", "parameter_uncertainty"], ["bayesian_doe_result"], "基于弱参数和工程约束排序候选实验。"),
        UIAction("run_constrained_window", "运行工程约束窗口", "sensitivity_optimization_page", "button_manual", "constrained_window", ["flowsheet_fast"], 5.0, ["constrained_windows"], ["SimulationState", "constraints"], ["constrained_windows"], "先快筛再用快速真实模型复核约束裕度。"),
        UIAction("train_surrogate", "训练物理约束代理模型", "sensitivity_optimization_page", "button_manual", "surrogate_training", ["sensitivity_results"], 2.0, ["surrogate_model"], ["sensitivity_result"], ["surrogate_model"], "只使用已有敏感性结果训练代理模型。"),
        UIAction("validate_surrogate", "验证代理模型物理约束", "sensitivity_optimization_page", "button_manual", "surrogate_validation", ["surrogate_model"], 0.5, ["surrogate_validation"], ["surrogate_model"], ["surrogate_validation"], "检查单调性和适用范围，不运行真实重模型。"),
        UIAction("save_case", "保存当前案例", "case_manager_page", "button_manual", "case_save", ["flowsheet_fast"], 0.5, [], ["SimulationState", "results_store"], ["case_json"], "保存配置、参数集和已有结果。"),
        UIAction("load_case", "加载案例", "case_manager_page", "data_import", "case_load", [], 0.5, ["flowsheet_fast"], ["case_json"], ["SimulationState"], "加载后只标记重任务过期。"),
        UIAction("export_excel", "导出Excel报告", "report_page", "export", "report_export", ["flowsheet_fast"], 1.0, [], ["existing_results"], ["xlsx"], "不主动重跑ODE/CFD/优化，缺失结果写未运行。"),
        UIAction("export_word", "导出Word报告", "report_page", "export", "report_export", ["flowsheet_fast"], 1.5, [], ["existing_results"], ["docx"], "优先嵌入已有图表，缺失时降级表格摘要。"),
        UIAction("export_repro_package", "导出复现实验包", "report_page", "export", "repro_package_export", ["flowsheet_fast"], 1.5, [], ["existing_results", "model_registry", "equation_registry"], ["repro_zip"], "只打包已有结果和快照，不主动重跑重模型。"),
        UIAction("export_openfoam", "导出OpenFOAM Case", "cfd_page", "export", "openfoam_export", ["cfd"], 1.0, [], ["cfd_inputs", "cfd_result"], ["openfoam_zip"], "只生成case skeleton，不运行OpenFOAM。"),
        UIAction("run_cfd_grid_convergence", "运行CFD网格独立性", "cfd_page", "button_manual", "cfd_grid_convergence", ["cfd"], 5.0, ["cfd_grid_convergence"], ["cfd_inputs", "reaction_template"], ["cfd_grid_convergence"], "细网格手动触发，不随页面加载运行。"),
        UIAction("run_engineering_rules", "运行化工趋势规则", "diagnostics", "button_manual", "engineering_rules", ["flowsheet_fast"], 3.0, ["engineering_rule_results"], ["SimulationState"], ["engineering_rule_results"], "一键趋势测试，只调用快速模型和轻量物性。"),
        UIAction("run_conservation_checks", "运行守恒闭合检查", "diagnostics/report", "auto_cached", "conservation", ["flowsheet_fast"], 0.2, [], ["flowsheet_result"], ["conservation_results"], "轻量检查，可随快速结果缓存刷新。"),
    ]


def get_ui_action(action_id: str) -> UIAction:
    """Return one UI action."""
    actions = {action.action_id: action for action in load_ui_actions()}
    return actions[action_id]


def ui_actions_dataframe(actions: list[UIAction] | None = None) -> pd.DataFrame:
    """Return UI actions as a DataFrame."""
    actions = load_ui_actions() if actions is None else actions
    return pd.DataFrame([action.as_dict() for action in actions])


def ui_registry_usability_dataframe(actions: list[UIAction] | None = None) -> pd.DataFrame:
    """Return usability and de-duplication checks for the UI action registry.

    The registry is the source of truth for user-triggered work.  These checks
    keep feature entry points intentional: every action needs a visible label,
    a target task, feedback text, and a distinct user-facing signature.
    """
    actions = load_ui_actions() if actions is None else actions
    rows: list[dict[str, Any]] = []

    def add(rule: str, passed: bool, detail: str, severity: str = "error") -> None:
        rows.append({"rule": rule, "passed": bool(passed), "severity": severity, "detail": detail})

    action_ids = [action.action_id for action in actions]
    duplicate_ids = sorted({action_id for action_id in action_ids if action_ids.count(action_id) > 1})
    add("action_id_unique", not duplicate_ids, f"duplicates={duplicate_ids}")

    missing_required = [
        action.action_id
        for action in actions
        if not action.label.strip() or not action.page.strip() or not action.trigger_type.strip() or not action.target_task.strip()
    ]
    add("required_fields_present", not missing_required, f"missing={missing_required}")

    missing_feedback = [action.action_id for action in actions if not action.user_feedback.strip()]
    add("user_feedback_present", not missing_feedback, f"missing={missing_feedback}", severity="warning")

    export_without_output = [action.action_id for action in actions if action.trigger_type == "export" and not action.writes]
    add("exports_declare_outputs", not export_without_output, f"missing_outputs={export_without_output}")

    signatures: list[tuple[str, str, str, tuple[str, ...], tuple[str, ...]]] = []
    for action in actions:
        signatures.append(
            (
                action.page,
                action.trigger_type,
                action.target_task,
                tuple(sorted(action.reads)),
                tuple(sorted(action.writes)),
            )
        )
    duplicate_signatures = sorted(
        {
            "|".join([page, trigger_type, target_task, ",".join(reads), ",".join(writes)])
            for page, trigger_type, target_task, reads, writes in signatures
            if signatures.count((page, trigger_type, target_task, reads, writes)) > 1
        }
    )
    add("no_duplicate_action_signature", not duplicate_signatures, f"duplicates={duplicate_signatures}")

    labels_by_page = [(action.page, action.label) for action in actions]
    duplicate_labels = sorted(
        {f"{page}|{label}" for page, label in labels_by_page if labels_by_page.count((page, label)) > 1}
    )
    add("labels_unique_per_page", not duplicate_labels, f"duplicates={duplicate_labels}")

    return pd.DataFrame(rows)
