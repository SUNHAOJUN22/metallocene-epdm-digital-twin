"""Sensitivity, single-objective optimization and Pareto page."""

from __future__ import annotations

import pandas as pd
import numpy as np
import plotly.express as px
import streamlit as st

from epdm_sim.flowsheet import ProcessConfig, run_flowsheet
from epdm_sim.optimizer import optimize_for_grade
from epdm_sim.pareto import generate_pareto_windows
from epdm_sim.plotting import optimization_convergence
from epdm_sim.polymer_props import load_target_grades
from epdm_sim.ui_theme import section_title
from epdm_sim.uncertainty import run_uncertainty_analysis
from epdm_sim.services.task_service import TaskService
from epdm_sim.utils import model_dump_compat


def render_sensitivity_optimization_page(config, result, save_config_callback=None, store=None) -> None:
    """Render on-demand sensitivity, optimization and Pareto calculations."""
    section_title("敏感性分析与多目标优化")
    tabs = st.tabs(["单变量扫描", "单目标优化", "Pareto工艺窗口", "模型可信度"])
    with tabs[0]:
        var = st.selectbox("扫描变量", ["temperature_C", "pressure_MPa", "enb_kg_h", "hydrogen_g_h", "residence_time_min"])
        span = st.slider("扫描点数", 5, 21, 9, 2)
        if st.button("运行单变量扫描", type="primary"):
            rows = []
            base = model_dump_compat(config)
            center = float(base[var])
            low = center * 0.65 if center > 0 else 0.0
            high = center * 1.45 + (1.0 if center == 0 else 0.0)
            for value in np.linspace(low, high, span):
                payload = dict(base)
                payload[var] = float(value)
                sim = run_flowsheet(ProcessConfig(**payload))
                row = {"value": value}
                row.update({key: sim.kpis[key] for key in ["C2_wt", "ENB_wt", "Mooney", "heat_duty_kW", "fouling_index"]})
                rows.append(row)
            st.session_state.sensitivity_df = pd.DataFrame(rows)
        df = st.session_state.get("sensitivity_df", pd.DataFrame())
        if not df.empty:
            st.plotly_chart(px.line(df, x="value", y=["ENB_wt", "Mooney", "fouling_index"], markers=True), width="stretch")
            st.dataframe(df, width="stretch")
    with tabs[1]:
        grades = list(load_target_grades())
        grade_id = st.selectbox("目标牌号", grades, index=grades.index(result.kpis.get("best_grade")) if result.kpis.get("best_grade") in grades else 0)
        if st.button("运行单目标优化", type="primary"):
            with st.spinner("优化器运行中..."):
                task = TaskService(st.session_state.setdefault("task_state", {}))
                st.session_state.optimization_result = task.run(
                    "optimization",
                    f"{grade_id}:{hash(str(model_dump_compat(config)))}",
                    lambda: optimize_for_grade(config, grade_id=grade_id, maxiter=5),
                )
                if store is not None:
                    store.optimization = st.session_state.optimization_result
        opt = st.session_state.get("optimization_result")
        if opt is not None:
            st.metric("优化匹配分数", f"{opt.score:.1f}", opt.message)
            st.plotly_chart(optimization_convergence(opt.history), width="stretch")
            st.dataframe(pd.DataFrame([opt.kpis]).drop(columns=["recommendations"], errors="ignore"), width="stretch")
    with tabs[2]:
        if st.button("生成Pareto工艺窗口", type="primary"):
            with st.spinner("生成多目标候选窗口..."):
                task = TaskService(st.session_state.setdefault("task_state", {}))
                pareto = task.run(
                    "pareto",
                    f"{result.kpis.get('best_grade', '')}:{hash(str(model_dump_compat(config)))}",
                    lambda: generate_pareto_windows(config, grade_id=result.kpis.get("best_grade", "Internal_1109_2_commercial_candidate"), n_samples=24),
                )
                st.session_state.pareto_result = pareto
        pareto = st.session_state.get("pareto_result")
        if pareto is not None:
            st.plotly_chart(px.scatter(pareto.frontier, x="ENB_wt", y="grade_score", color="fouling_index", size="cooling_margin_kW"), width="stretch")
            st.subheader("推荐窗口")
            st.dataframe(pareto.recommended_windows, width="stretch")
            st.subheader("Pareto frontier")
            st.dataframe(pareto.frontier, width="stretch")
    with tabs[3]:
        n_samples = st.slider("不确定性样本数", 8, 80, 24, 4)
        seed = st.number_input("随机种子", 1, 9999, 7, 1)
        if st.button("运行模型可信度分析", type="primary"):
            with st.spinner("运行Monte Carlo/Latin Hypercube扰动..."):
                task = TaskService(st.session_state.setdefault("task_state", {}))
                st.session_state.uncertainty_result = task.run(
                    "uncertainty",
                    f"{n_samples}:{seed}:{hash(str(model_dump_compat(config)))}",
                    lambda: run_uncertainty_analysis(config, n_samples=n_samples, seed=int(seed)),
                )
        unc = st.session_state.get("uncertainty_result")
        if unc is not None:
            st.metric("模型适用性评分", f"{unc.model_confidence['applicability_score']:.2f}")
            st.dataframe(unc.as_dataframe(), width="stretch")
            st.plotly_chart(px.bar(unc.tornado, x="factor", y="importance", color="correlation", title="Tornado sensitivity proxy"), width="stretch")
            st.dataframe(pd.DataFrame([unc.risk_probabilities]), width="stretch")
        else:
            st.info("不确定性分析按按钮触发，不会随页面切换自动运行。")

