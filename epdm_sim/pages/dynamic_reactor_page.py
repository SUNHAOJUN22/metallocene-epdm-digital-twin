"""Dynamic batch/semi-batch reactor page."""

from __future__ import annotations

import plotly.express as px
import streamlit as st

from epdm_sim.dynamic_reactor import DynamicReactorConfig, simulate_dynamic_reactor, stage_timeline
from epdm_sim.equipment_3d import reactor_3d_figure
from epdm_sim.recipe import default_semibatch_recipe, recipe_event_log, recipe_from_dataframe, recipe_from_json, recipe_to_dataframe, recipe_to_ode_config
from epdm_sim.reactor import simulate_dynamic_semibatch_ode
from epdm_sim.services.cache_keys import detail_cache_key
from epdm_sim.services.task_service import TaskService
from epdm_sim.ui_theme import section_title


def render_dynamic_reactor_page(config, result, save_config_callback=None, store=None) -> None:
    """Render dynamic stirred-tank timelines with manual ODE trigger."""
    section_title("釜式聚合工艺时序")
    c1, c2 = st.columns([1, 1.4])
    with c1:
        model = st.radio("动态模型", ["快速准动态模型", "ODE详细模型"], horizontal=True)
        total_time = st.slider("总批次时间 min", 30, 180, int(max(config.residence_time_min, 60)))
        rpm = st.slider("搅拌转速 rpm", 100, 1200, int(getattr(config, "agitation_rpm", 500)), 25)
        enb_strategy = st.selectbox("ENB策略", ["一次加入", "连续加入", "分段加入"])
        with st.expander("Recipe编辑/导入导出", expanded=False):
            if "recipe_df" not in st.session_state:
                st.session_state.recipe_df = recipe_to_dataframe(default_semibatch_recipe(total_time))
            uploaded_recipe = st.file_uploader("导入recipe JSON", type=["json"])
            if uploaded_recipe is not None:
                st.session_state.recipe_df = recipe_to_dataframe(recipe_from_json(uploaded_recipe.read().decode("utf-8")))
            edited_recipe_df = st.data_editor(st.session_state.recipe_df, width="stretch", num_rows="dynamic")
            st.session_state.recipe_df = edited_recipe_df
            recipe_obj = recipe_from_dataframe(edited_recipe_df)
            st.download_button("导出recipe JSON", recipe_obj.to_json(), file_name="epdm_recipe.json", mime="application/json")
            st.dataframe(recipe_event_log(recipe_obj), width="stretch")
        if st.button("运行釜式动态模型", type="primary"):
            recipe_obj = recipe_from_dataframe(st.session_state.get("recipe_df", recipe_to_dataframe(default_semibatch_recipe(total_time))))
            key = detail_cache_key(config, {"dynamic": model, "time": total_time, "rpm": rpm, "enb": enb_strategy})
            with st.spinner("运行动态釜式模型..."):
                task = TaskService(st.session_state.setdefault("task_state", {}))

                def _run_dynamic():
                    if model == "ODE详细模型":
                        return simulate_dynamic_semibatch_ode(
                            config,
                            recipe_to_ode_config(recipe_obj, total_time_min=total_time, rpm=rpm, enb_strategy=enb_strategy) | {"n_eval": 121},
                        )
                    return simulate_dynamic_reactor(
                        config,
                        DynamicReactorConfig(total_time_min=total_time, rpm=rpm, enb_feed_strategy=enb_strategy),
                    )

                dyn = task.run("dynamic_ode" if model == "ODE详细模型" else "dynamic_fast", key, _run_dynamic)
                profile = dyn.profile
                summary = dyn.summary
                st.session_state.dynamic_profile = profile
                st.session_state.dynamic_summary = summary
                if store is not None:
                    store.dynamic_key = key
                    store.dynamic = dyn
    with c2:
        st.plotly_chart(reactor_3d_figure(result, mode="黏度/挂胶风险模式"), width="stretch")
    profile = st.session_state.get("dynamic_profile")
    if profile is None:
        st.info("动态模型按需运行，不会随页面切换或滑块变化自动重算。")
        st.dataframe(stage_timeline(total_time), width="stretch")
        return
    tabs = st.tabs(["温度/热负荷", "组成/转化", "流变/门尼", "阶段表"])
    with tabs[0]:
        st.plotly_chart(px.line(profile, x=profile.columns[0], y=[c for c in ["T_C", "Q_rxn_kW"] if c in profile], markers=True), width="stretch")
    with tabs[1]:
        ycols = [c for c in ["C_E_mol_L", "C_P_mol_L", "C_ENB_mol_L", "conversion_pct"] if c in profile]
        st.plotly_chart(px.line(profile, x=profile.columns[0], y=ycols), width="stretch")
    with tabs[2]:
        ycols = [c for c in ["viscosity_Pa_s", "Mw", "Mooney", "fouling_index"] if c in profile]
        st.plotly_chart(px.line(profile, x=profile.columns[0], y=ycols), width="stretch")
    with tabs[3]:
        st.dataframe(profile, width="stretch", height=360)

