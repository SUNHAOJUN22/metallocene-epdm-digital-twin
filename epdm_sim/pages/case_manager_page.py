"""Case and scenario management page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from epdm_sim.case_manager import compare_cases, duplicate_case, export_case_package, import_case_package_zip, list_cases, load_case, save_case
from epdm_sim.flowsheet import ProcessConfig


def render_case_manager_page(current_config: ProcessConfig, result, save_config_callback) -> None:
    """Render case save/load/compare UI."""
    st.title("案例与场景管理")
    st.caption("加载案例只更新快速流程配置，不会自动运行CFD、优化器或报告生成。")
    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("保存当前案例")
        name = st.text_input("案例名称", value="case_base")
        notes = st.text_area("备注", value="")
        if st.button("保存当前案例", type="primary"):
            record = save_case(name, current_config, result=result, parameter_set_id=current_config.parameter_set_id, notes=notes)
            st.success(f"已保存案例：{record.case_id}")
    cases = list_cases()
    with c2:
        st.subheader("已保存案例")
        if cases.empty:
            st.info("尚无保存案例。")
        else:
            shown = cases.copy()
            if "created_at" in shown:
                shown["created_at"] = pd.to_datetime(shown["created_at"], unit="s", errors="coerce")
            st.dataframe(shown, width="stretch", height=260)
        uploaded = st.file_uploader("导入案例包 zip", type=["zip"])
        if uploaded is not None and st.button("导入案例包"):
            imported = import_case_package_zip(uploaded.getvalue())
            st.success(f"已导入案例包：{imported.case_id}")
    if cases.empty:
        return
    st.divider()
    st.subheader("加载 / 复制 / 对比")
    case_ids = cases["case_id"].tolist()
    c1, c2, c3 = st.columns(3)
    selected = c1.selectbox("加载案例", case_ids)
    if c1.button("加载到当前配置"):
        record = load_case(selected)
        save_config_callback(ProcessConfig(**record.config))
        st.success(f"已加载案例：{record.case_name}")
    record_for_export = load_case(selected)
    c1.download_button("导出案例包", export_case_package(record_for_export), f"{record_for_export.case_id}_package.zip")
    copy_name = c2.text_input("复制为", value=f"{selected}_copy")
    if c2.button("复制案例"):
        duplicate_case(selected, copy_name)
        st.success("已复制案例。")
    compare_a = c3.selectbox("案例A", case_ids, index=0)
    compare_b = c3.selectbox("案例B", case_ids, index=min(1, len(case_ids) - 1))
    if st.button("对比两个案例", type="primary"):
        comp = compare_cases(load_case(compare_a), load_case(compare_b))
        st.session_state.case_comparison_df = comp
    comp_df = st.session_state.get("case_comparison_df", pd.DataFrame())
    if not comp_df.empty:
        st.dataframe(comp_df, width="stretch")

