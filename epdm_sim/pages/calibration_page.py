"""Parameter set management and nonlinear estimation page components."""

from __future__ import annotations

import time

import pandas as pd
import plotly.express as px
import streamlit as st

from epdm_sim.experiment_data import load_internal_experiment_dataset
from epdm_sim.parameter_estimation import (
    estimate_parameters,
    parameter_sets_dataframe,
    save_parameter_set,
    set_active_parameter_set,
)
from epdm_sim.flowsheet import ProcessConfig
from epdm_sim.services.task_service import TaskService


@st.cache_data(show_spinner=False, max_entries=16)
def _cached_estimation(data_json: str, target: str, method: str, model_mode: str):
    df = pd.read_json(data_json)
    return estimate_parameters(
        df,
        target=target,
        method=method,
        model_mode=model_mode,
        max_nfev=30 if model_mode == "empirical_proxy" else 5,
        max_seconds=12 if model_mode != "empirical_proxy" else None,
        dataset_id="ui_experiment_dataset",
    )


def render_parameter_management(current_config: ProcessConfig, save_config_callback) -> None:
    """Render parameter-set registry and nonlinear estimation controls."""
    st.subheader("参数集管理")
    registry_df = parameter_sets_dataframe()
    if registry_df.empty:
        st.info("尚未建立参数集 registry。")
    else:
        st.dataframe(registry_df, width="stretch")
    set_ids = registry_df["set_id"].tolist() if not registry_df.empty else ["default"]
    selected = st.selectbox(
        "当前模拟使用参数集",
        set_ids,
        index=set_ids.index(current_config.parameter_set_id) if current_config.parameter_set_id in set_ids else 0,
    )
    c1, c2 = st.columns(2)
    if c1.button("设为当前模拟参数集", type="primary"):
        set_active_parameter_set(selected)
        current_config.parameter_set_id = selected
        save_config_callback(current_config)
        st.success(f"已切换参数集：{selected}")
    if c2.button("刷新参数集列表"):
        st.rerun()

    st.divider()
    st.subheader("非线性参数估计")
    exp_df = st.session_state.get("experiment_df", load_internal_experiment_dataset())
    c1, c2, c3 = st.columns(3)
    target = c1.selectbox("拟合目标", ["combined", "C2_wt", "ENB_wt", "Mooney", "Mw", "PDI", "activity"], index=0)
    method = c2.selectbox("全局/局部策略", ["least_squares", "differential_evolution"], index=0)
    set_name = c3.text_input("保存参数集ID", value=f"user_calibrated_{int(time.time())}")
    model_mode = st.selectbox("拟合模型", ["empirical_proxy", "flowsheet_real", "dynamic_ode_real", "hybrid"], index=0)
    if st.button("运行非线性参数估计", type="primary"):
        with st.spinner("正在进行非线性参数估计..."):
            task = TaskService(st.session_state.setdefault("task_state", {}))
            p_hash = f"{target}:{method}:{model_mode}:{hash(exp_df.to_json())}"
            st.session_state.parameter_estimation_result = task.run(
                "parameter_estimation",
                p_hash,
                lambda: _cached_estimation(exp_df.to_json(), target, method, model_mode),
            )
    estimation = st.session_state.get("parameter_estimation_result")
    if estimation is None:
        st.info("点击按钮后执行参数估计；不会随页面切换或滑块变化自动运行。")
        return
    st.caption(f"model_mode={estimation.model_mode}；fitting_runtime={estimation.fitting_runtime_s:.2f}s")
    for warning in estimation.warnings:
        st.warning(warning)
    m1, m2 = st.columns(2)
    m1.dataframe(estimation.metrics_dataframe(), width="stretch")
    m2.dataframe(estimation.confidence_dataframe(), width="stretch", height=300)
    st.dataframe(estimation.params_dataframe(), width="stretch")
    if not estimation.confidence_interval.empty:
        st.subheader("参数置信区间 proxy")
        ci = estimation.confidence_interval.copy()
        st.plotly_chart(px.bar(ci, x="parameter", y="estimate", error_y=ci["high"] - ci["estimate"], error_y_minus=ci["estimate"] - ci["low"]), width="stretch")
    if not estimation.parameter_correlation.empty:
        st.subheader("参数相关性矩阵")
        corr = estimation.parameter_correlation.set_index("parameter")
        st.plotly_chart(px.imshow(corr, aspect="auto", color_continuous_scale="RdBu", zmin=-1, zmax=1), width="stretch")
    if not estimation.residuals.empty:
        st.subheader("残差图")
        st.plotly_chart(px.scatter(estimation.residuals, x="observed", y="predicted", color="target", hover_data=["run_id"]), width="stretch")
        st.dataframe(estimation.residuals, width="stretch", height=260)
    if not estimation.run_failures.empty:
        st.subheader("真实模型拟合失败样本")
        st.dataframe(estimation.run_failures, width="stretch")
    if st.button("保存估计结果为参数集"):
        save_parameter_set(
            set_name,
            estimation.fitted_params,
            description=f"Nonlinear estimation target={target}, method={method}",
            source="nonlinear-estimation",
            metrics={row["target"]: {"r2": row["r2"], "mae": row["mae"]} for _, row in estimation.metrics_dataframe().iterrows()},
            dataset_id=estimation.dataset_id,
            fit_method=model_mode,
            model_mode=estimation.model_mode,
            fitting_runtime_s=estimation.fitting_runtime_s,
            run_failures=estimation.run_failures,
            fitted_targets=[target],
            confidence_interval=estimation.confidence_interval,
            make_active=True,
        )
        current_config.parameter_set_id = set_name
        save_config_callback(current_config)
        st.success(f"已保存并启用参数集：{set_name}")

