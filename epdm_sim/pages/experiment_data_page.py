"""Experiment data management page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from epdm_sim.db import import_experiments_dataframe, list_model_runs, query_experiments
from epdm_sim.experiment_data import (
    calibration_subset,
    load_internal_experiment_dataset,
    normalize_experiments,
    quality_check_experiments,
)


def render_experiment_data_page() -> None:
    """Render experiment data import, normalization and quality diagnostics."""
    st.title("实验数据管理")
    st.caption("导入和质检不会自动触发参数校准；校准必须在参数管理区手动运行。")
    source = st.radio("数据来源", ["内置实验数据", "上传CSV/Excel"], horizontal=True)
    uploaded_df = None
    if source == "上传CSV/Excel":
        uploaded = st.file_uploader("上传实验数据文件", type=["csv", "xlsx", "xls"])
        if uploaded is not None:
            if uploaded.name.lower().endswith((".xlsx", ".xls")):
                uploaded_df = pd.read_excel(uploaded)
            else:
                uploaded_df = pd.read_csv(uploaded)
    if st.button("读取并检查实验数据", type="primary") or "experiment_df" not in st.session_state:
        if source == "上传CSV/Excel" and uploaded_df is not None:
            normalized = normalize_experiments(uploaded_df)
        else:
            normalized = load_internal_experiment_dataset()
        report = quality_check_experiments(normalized)
        st.session_state.experiment_df = normalized
        st.session_state.data_quality_report = report
    df = st.session_state.get("experiment_df", load_internal_experiment_dataset())
    report = st.session_state.get("data_quality_report", quality_check_experiments(df))
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("实验行数", len(df))
    k2.metric("可校准行数", len(calibration_subset(df)))
    k3.metric("缺失字段", len(report.missing_fields))
    k4.metric("异常/越界", len(report.outliers) + len(report.impossible_values))
    st.subheader("标准化实验数据")
    st.dataframe(df, width="stretch", height=360)
    st.subheader("数据质量诊断")
    qdf = report.as_dataframe()
    if qdf.empty:
        st.success("未发现明显结构性问题。")
    else:
        st.dataframe(qdf, width="stretch")
    st.subheader("可用于校准的数据子集")
    st.dataframe(calibration_subset(df), width="stretch", height=260)
    with st.expander("本地SQLite数据仓库", expanded=False):
        st.caption("SQLite用于本地可追溯数据仓库；导入不会自动触发校准或重计算。")
        c1, c2 = st.columns(2)
        if c1.button("导入当前实验表到SQLite"):
            count = import_experiments_dataframe(df)
            st.success(f"已导入/更新 {count} 条实验记录。")
        if c2.button("查询SQLite实验记录"):
            st.session_state.sqlite_experiment_df = query_experiments()
        sqlite_df = st.session_state.get("sqlite_experiment_df")
        if sqlite_df is not None:
            st.dataframe(sqlite_df, width="stretch", height=260)
        st.subheader("历史模型运行")
        try:
            st.dataframe(list_model_runs(), width="stretch")
        except Exception as exc:
            st.caption(f"暂无历史运行或数据库尚未初始化：{exc}")

