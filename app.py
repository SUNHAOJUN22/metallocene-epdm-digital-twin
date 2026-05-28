"""Streamlit entrypoint for the Metallocene EPDM Digital Twin."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from epdm_sim.conservation import conservation_dataframe, run_conservation_checks
from epdm_sim.engineering_checks import checks_dataframe, overall_engineering_status, run_engineering_checks
from epdm_sim.engineering_rules import rules_dataframe, rule_results_dataframe, run_all_engineering_rules
from epdm_sim.flowsheet import ProcessConfig, load_default_config
from epdm_sim.model_confidence import build_model_confidence_card
from epdm_sim.model_registry import module_trigger_dataframe, registry_summary
from epdm_sim.pages.calibration_page import render_parameter_management
from epdm_sim.pages.case_manager_page import render_case_manager_page
from epdm_sim.pages.cfd_page import render_cfd_page
from epdm_sim.pages.dashboard_page import render_dashboard_page
from epdm_sim.pages.dynamic_reactor_page import render_dynamic_reactor_page
from epdm_sim.pages.experiment_data_page import render_experiment_data_page
from epdm_sim.pages.equipment_library_page import render_equipment_library_page
from epdm_sim.pages.heat_fluid_page import render_heat_fluid_page
from epdm_sim.pages.model_governance_page import render_model_governance_page
from epdm_sim.pages.product_page import render_product_page
from epdm_sim.pages.reactor_page import render_reactor_page
from epdm_sim.pages.report_page import render_report_page
from epdm_sim.pages.separation_page import render_separation_page
from epdm_sim.pages.sensitivity_optimization_page import render_sensitivity_optimization_page
from epdm_sim.pages.workflow_wizard_page import render_page as render_workflow_wizard_page
from epdm_sim.services.simulation_service import performance_rows, run_flowsheet_with_store
from epdm_sim.services.task_service import TaskService, task_graph_dataframe
from epdm_sim.state import ResultsStore, SimulationState
from epdm_sim.ui_theme import apply_theme, top_bar
from epdm_sim.ui_workflow import ui_actions_dataframe
from epdm_sim.utils import model_dump_compat
from epdm_sim.preflight import preflight_dataframe, run_preflight_for_flowsheet


ASSUMPTIONS_TEXT = (
    "本软件为研发级茂金属EPDM/EPM溶液聚合过程仿真与数字孪生工具，用于趋势判断、实验设计、"
    "工艺窗口筛选、牌号反推和工程风险识别。动力学参数、热力学参数、胶液黏度、反应热、闪蒸回收、"
    "CFD场分布和3D装置均采用简化模型或默认估算值，必须用更多实验数据校准。软件不能直接替代"
    "Aspen Plus、Aspen Polymers、Fluent、OpenFOAM或工业设计包。工业放大必须结合真实物性、"
    "真实反应器几何、真实搅拌桨、真实流变数据和中试验证。"
)


def _init_session() -> None:
    """Initialize session state once."""
    if "sim_state" not in st.session_state:
        st.session_state.sim_state = SimulationState.from_process_config(load_default_config())
    if "results_store" not in st.session_state:
        st.session_state.results_store = ResultsStore()
    if "page_triggered_recompute" not in st.session_state:
        st.session_state.page_triggered_recompute = False
    if "task_state" not in st.session_state:
        st.session_state.task_state = {}


def _current_config() -> ProcessConfig:
    return ProcessConfig(**st.session_state.sim_state.config)


def _save_config(config: ProcessConfig) -> None:
    """Persist edited config and invalidate fast/detail results."""
    st.session_state.sim_state.update_config(config)
    st.session_state.results_store.invalidate_flowsheet()
    st.session_state.results_store.invalidate_detail()


def _sidebar(config: ProcessConfig) -> str:
    """Render global navigation and process controls."""
    st.sidebar.title("EPDM Digital Twin")
    page = st.sidebar.radio("导航", list(PAGES.keys()), index=0)
    st.sidebar.divider()
    st.session_state.sim_state.run_mode = st.sidebar.radio("运行模式", ["快速模式", "详细模式"], horizontal=True)
    st.session_state.sim_state.theme = st.sidebar.radio("主题", ["深色", "浅色"], horizontal=True)
    st.session_state.sim_state.case_name = st.sidebar.text_input("当前案例名", st.session_state.sim_state.case_name)
    with st.sidebar.expander("全局快速输入", expanded=True):
        cfg = ProcessConfig(**model_dump_compat(config))
        cfg.temperature_C = st.number_input("反应温度 °C", 60.0, 180.0, float(cfg.temperature_C), 1.0)
        cfg.pressure_MPa = st.number_input("反应压力 MPa", 0.1, 5.0, float(cfg.pressure_MPa), 0.05)
        cfg.ethylene_kg_h = st.number_input("乙烯 kg/h", 0.0, 500.0, float(cfg.ethylene_kg_h), 1.0)
        cfg.propylene_kg_h = st.number_input("丙烯 kg/h", 0.0, 500.0, float(cfg.propylene_kg_h), 1.0)
        cfg.enb_kg_h = st.number_input("ENB kg/h", 0.0, 100.0, float(cfg.enb_kg_h), 0.1)
        cfg.hydrogen_g_h = st.number_input("氢气 g/h", 0.0, 500.0, float(cfg.hydrogen_g_h), 0.5)
        cfg.reactor_mode = st.selectbox(
            "反应器模式",
            ["Semi-batch Reactor", "Batch reactor", "CSTR", "CSTR series", "Fed-batch Grade Transition"],
            index=0 if cfg.reactor_mode not in ["Batch reactor", "CSTR", "CSTR series", "Fed-batch Grade Transition"] else ["Semi-batch Reactor", "Batch reactor", "CSTR", "CSTR series", "Fed-batch Grade Transition"].index(cfg.reactor_mode),
        )
        if st.button("运行快速流程模拟", type="primary"):
            _save_config(cfg)
            st.session_state.page_triggered_recompute = True
            st.rerun()
    with st.sidebar.expander("模型假设与局限性"):
        st.write(ASSUMPTIONS_TEXT)
    with st.sidebar.expander("模型模块与点击策略"):
        summary = registry_summary()
        st.caption(
            f"统一入口：digital-twin；已合并 process-simulator 基线。"
            f"当前注册 {summary['module_count']} 个模型/数据/导出模块。"
        )
        st.dataframe(
            module_trigger_dataframe()[["模块", "类别", "触发方式", "适用范围"]],
            width="stretch",
            hide_index=True,
        )
        if summary["validation_errors"]:
            st.warning("模型注册表存在数据问题，请检查 data/model_registry.json。")
    return page


def _performance_panel(result=None) -> None:
    """Render global performance diagnostics."""
    with st.expander("性能诊断", expanded=False):
        rows = performance_rows(st.session_state.sim_state, st.session_state.results_store, st.session_state.page_triggered_recompute)
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
        st.subheader("运行状态与任务图")
        st.dataframe(task_graph_dataframe(), width="stretch", hide_index=True)
        task_df = TaskService(st.session_state.task_state).as_dataframe()
        st.session_state.task_service_log = task_df
        if not task_df.empty:
            st.subheader("长任务状态")
            st.dataframe(task_df, width="stretch", hide_index=True)
        if result is not None:
            st.subheader("前置输入校验")
            preflight = run_preflight_for_flowsheet(result.config)
            st.dataframe(preflight_dataframe(preflight), width="stretch", hide_index=True)
            st.subheader("工程逻辑检查")
            checks = run_engineering_checks(result)
            status = overall_engineering_status(checks)
            st.caption({"green": "工程逻辑检查通过", "yellow": "存在工程警告", "red": "存在工程错误"}[status])
            st.dataframe(checks_dataframe(checks), width="stretch", hide_index=True)
            st.subheader("守恒闭合检查")
            conservation = run_conservation_checks(result)
            st.dataframe(conservation_dataframe(conservation), width="stretch", hide_index=True)
            st.subheader("模型可信度卡片")
            confidence = build_model_confidence_card(
                result,
                engineering_checks=checks,
                conservation_results=conservation,
                preflight_results=preflight,
                parameter_set_source=result.kpis.get("parameter_set_id", "default"),
            )
            st.dataframe(confidence.as_dataframe(), width="stretch", hide_index=True)
            st.subheader("化工趋势规则库")
            st.dataframe(rules_dataframe()[["rule_id", "description", "module_id", "expected_trend", "severity"]], width="stretch", hide_index=True)
            if st.button("运行化工趋势规则检查", key="run_engineering_rules_global"):
                service = TaskService(st.session_state.task_state)
                st.session_state.engineering_rule_results = service.run(
                    "engineering_rules",
                    st.session_state.sim_state.fingerprint(),
                    lambda: run_all_engineering_rules(_current_config()),
                    dependency_hash=st.session_state.sim_state.fingerprint(),
                    use_cache=True,
                )
            if "engineering_rule_results" in st.session_state:
                st.dataframe(rule_results_dataframe(st.session_state.engineering_rule_results), width="stretch", hide_index=True)
        st.subheader("UI点击动作注册表")
        st.dataframe(ui_actions_dataframe()[["action_id", "label", "trigger_type", "target_task", "expected_runtime_s", "user_feedback"]], width="stretch", hide_index=True)
        st.caption("ODE、CFD、优化、参数估计和报告图导出均为按钮触发；页面切换只复用当前结果。")


def _render_current_page(page: str, config: ProcessConfig, result) -> None:
    """Dispatch page rendering."""
    if page in {"实验数据管理", "参数集与非线性估计", "案例与场景管理", "研发工作流向导"}:
        if page == "实验数据管理":
            render_experiment_data_page()
        elif page == "参数集与非线性估计":
            render_parameter_management(config, _save_config)
        elif page == "研发工作流向导":
            render_workflow_wizard_page(st, {"available_results": {"run_fast_flowsheet": bool(result)}})
        else:
            render_case_manager_page(config, result, _save_config)
        return
    PAGES[page](config, result, _save_config, st.session_state.results_store)


def main() -> None:
    """Run the Streamlit app."""
    st.set_page_config(
        page_title="Metallocene EPDM Digital Twin",
        page_icon="EPDM",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _init_session()
    config = _current_config()
    apply_theme(st.session_state.sim_state.theme)
    page = _sidebar(config)
    top_bar(st.session_state.sim_state.case_name, st.session_state.sim_state.run_mode, st.session_state.sim_state.theme)
    timed = run_flowsheet_with_store(_current_config(), st.session_state.results_store)
    st.session_state.sim_state.mark_clean("flowsheet", "heat_balance", "fluid_props", "flash", "product")
    _render_current_page(page, timed.result.config, timed.result)
    _performance_panel(timed.result)
    st.session_state.page_triggered_recompute = False


PAGES = {
    "数字孪生总览": render_dashboard_page,
    "釜式聚合工艺时序": render_dynamic_reactor_page,
    "反应器与动力学": render_reactor_page,
    "热量衡算与流体性质": render_heat_fluid_page,
    "分离脱挥与回收": render_separation_page,
    "产品性能与美孚对标": render_product_page,
    "实验数据管理": None,
    "参数集与非线性估计": None,
    "案例与场景管理": None,
    "研发工作流向导": None,
    "模型治理与可信度证书": render_model_governance_page,
    "CFD有限元可视化": render_cfd_page,
    "敏感性分析与优化": render_sensitivity_optimization_page,
    "3D装置库": render_equipment_library_page,
    "报告导出": render_report_page,
}


if __name__ == "__main__":
    main()

