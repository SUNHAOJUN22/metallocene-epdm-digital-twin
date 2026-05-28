"""Separation, flash, recycle and thermodynamics page."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from epdm_sim.eos import eos_details_table, k_value_comparison
from epdm_sim.plotting import flash_split_chart
from epdm_sim.solubility import gas_liquid_saturation_table, gas_mole_fractions_from_feeds, henry_cstar_comparison
from epdm_sim.ui_theme import kpi_grid, section_title


def render_separation_page(config, result, save_config_callback=None, store=None) -> None:
    """Render thermodynamics, flash split and recycle diagnostics."""
    k = result.kpis
    section_title("热力学、分离脱挥与回收")
    kpi_grid(
        [
            ("Thermo模式", str(k["thermo_mode"]), "Wilson/EOS/thermo", "#22d3ee"),
            ("Flash-1气化率", f"{k['flash1_vapor_fraction']:.2f}", "monomer recovery", "#60a5fa"),
            ("Flash-2气化率", f"{k['flash2_vapor_fraction']:.2f}", "devolatilization", "#a78bfa"),
            ("单体回收", f"{k['monomer_recovery_pct']:.1f}%", "recycle", "#22c55e"),
            ("溶剂回收", f"{k['solvent_recovery_pct']:.1f}%", "recycle", "#f59e0b"),
            ("ENB残留", f"{k['ENB_residue_ppm']:.0f} ppm", "product", "#fb923c"),
        ]
    )
    tabs = st.tabs(["Henry/EOS", "Flash-1", "Flash-2", "回收循环"])
    with tabs[0]:
        y = gas_mole_fractions_from_feeds(config.ethylene_kg_h, config.propylene_kg_h, config.hydrogen_g_h)
        st.dataframe(gas_liquid_saturation_table(config.temperature_C + 273.15, config.pressure_MPa, y, config.solvent), width="stretch")
        names = ["ethylene", "propylene", "hydrogen", "ENB", config.solvent]
        eos_mode = st.selectbox("EOS模式", ["PR", "SRK"])
        eos_df = pd.DataFrame(eos_details_table(names, config.temperature_C + 273.15, config.pressure_MPa * 1e6, eos_mode))
        st.dataframe(eos_df, width="stretch")
        k_cmp = pd.DataFrame.from_dict(k_value_comparison(names, config.temperature_C + 273.15, config.pressure_MPa * 1e6), orient="index").reset_index(names="component")
        st.plotly_chart(px.bar(k_cmp, x="component", y=["Wilson", "PR", "SRK"], barmode="group", log_y=True, title="K-value对比"), width="stretch")
        henry_df = henry_cstar_comparison(config.temperature_C + 273.15, config.pressure_MPa, y, config.solvent)
        st.plotly_chart(px.bar(henry_df, x="component", y=["Cstar_base_mol_L", "Cstar_corrected_mol_L"], barmode="group", title="Henry Cstar对比"), width="stretch")
        st.warning("Henry/EOS均为研发级简化模型；聚合物溶液、ENB活度、kij和高压VLE需要实验校准。当前模型适用性等级：研发趋势筛选。")
    with tabs[1]:
        st.plotly_chart(flash_split_chart(result.flash1), width="stretch")
        st.dataframe(result.flash1.split_table, width="stretch")
    with tabs[2]:
        st.plotly_chart(flash_split_chart(result.flash2), width="stretch")
        st.dataframe(result.flash2.split_table, width="stretch")
    with tabs[3]:
        recycle = result.recycle_solver
        if recycle is not None:
            st.dataframe(recycle.as_dataframe(), width="stretch")
            st.plotly_chart(px.line(recycle.history, x="iteration", y="closure_error", markers=True, title="回收循环闭合误差"), width="stretch")

