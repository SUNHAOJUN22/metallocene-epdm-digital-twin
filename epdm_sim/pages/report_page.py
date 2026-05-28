"""Report export page."""

from __future__ import annotations

import streamlit as st

from epdm_sim import APP_VERSION
from epdm_sim.plotting import sankey_material
from epdm_sim.services.report_service import export_bundle, figure_export_status
from epdm_sim.services.task_service import TaskService
from epdm_sim.ui_theme import section_title


def render_report_page(config, result, save_config_callback=None, store=None) -> None:
    """Render report export controls without rerunning heavy calculations."""
    section_title("报告导出")
    include_figures = st.toggle("尝试导出Plotly静态图", value=False)
    figures = {"物料Sankey": sankey_material(result)} if include_figures else {}
    for note in figure_export_status(figures):
        st.caption(note)
    common = {
        "sensitivity_df": st.session_state.get("sensitivity_df"),
        "optimization": st.session_state.get("optimization_result"),
        "parameter_estimation": st.session_state.get("parameter_estimation_result"),
        "dynamic_semibatch_df": st.session_state.get("dynamic_profile"),
        "case_comparison": st.session_state.get("case_comparison_df"),
        "safety": st.session_state.get("safety_result"),
        "pareto_df": getattr(st.session_state.get("pareto_result"), "frontier", None),
        "uncertainty": st.session_state.get("uncertainty_result"),
        "recipe_df": st.session_state.get("recipe_df"),
        "task_log": st.session_state.get("task_service_log"),
        "manifest": {
            "app_version": APP_VERSION,
            "parameter_set_id": getattr(config, "parameter_set_id", "default"),
            "case_name": st.session_state.get("sim_state").case_name if st.session_state.get("sim_state") is not None else "",
        },
    }
    c1, c2, c3 = st.columns(3)
    if c1.button("生成Excel", type="primary"):
        task = TaskService(st.session_state.setdefault("task_state", {}))
        st.session_state.report_excel = task.run("report_excel", f"excel:{hash(str(result.kpis))}", lambda: export_bundle(result, report_type="excel", **common), use_cache=False)
    if c2.button("生成Word", type="primary"):
        task = TaskService(st.session_state.setdefault("task_state", {}))
        st.session_state.report_word = task.run("report_word", f"word:{hash(str(result.kpis))}", lambda: export_bundle(result, report_type="word", figures=figures, **common), use_cache=False)
    if c3.button("生成PDF", type="primary"):
        task = TaskService(st.session_state.setdefault("task_state", {}))
        st.session_state.report_pdf = task.run("report_pdf", f"pdf:{hash(str(result.kpis))}", lambda: export_bundle(result, report_type="pdf", figures=figures, **common), use_cache=False)
    if "report_excel" in st.session_state:
        st.download_button("下载Excel", st.session_state.report_excel, "epdm_digital_twin_report.xlsx")
    if "report_word" in st.session_state:
        st.download_button("下载Word", st.session_state.report_word, "epdm_digital_twin_report.docx")
    if "report_pdf" in st.session_state:
        st.download_button("下载PDF", st.session_state.report_pdf, "epdm_digital_twin_report.pdf")
