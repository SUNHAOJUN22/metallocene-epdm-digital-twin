"""Heat balance, fluid properties and safety page."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from epdm_sim.safety import calculate_safety
from epdm_sim.ui_theme import kpi_grid, section_title


def render_heat_fluid_page(config, result, save_config_callback=None, store=None) -> None:
    """Render energy, fluid-property, hydraulics and thermal safety diagnostics."""
    k = result.kpis
    section_title("热量衡算与流体性质")
    kpi_grid(
        [
            ("反应热", f"{k['heat_duty_kW']:.2f} kW", "需移走", "#ef4444"),
            ("预热/脱挥", f"{k['preheat_kW']:.2f}/{k['devol_duty_kW']:.2f}", "kW", "#f59e0b"),
            ("绝热温升", f"{k['deltaT_ad_K']:.1f} K", k["thermal_risk"], "#fb923c"),
            ("移热裕度", f"{k['cooling_margin_kW']:.2f} kW", k["heat_transfer_status"], "#22d3ee"),
            ("密度/Cp", f"{k['liquid_density_kg_m3']:.0f}/{k['Cp_liq_kJ_kgK']:.2f}", "kg/m3, kJ/kg/K", "#60a5fa"),
            ("黏度/压降", f"{k['dynamic_viscosity_Pa_s']:.3g}/{k['pipe_pressure_drop_kPa']:.1f}", "Pa.s / kPa", "#a78bfa"),
        ]
    )
    tabs = st.tabs(["热量表", "流体性质", "压降泵送", "热安全", "趋势曲线"])
    with tabs[0]:
        st.dataframe(result.heat_balance_table(), width="stretch")
    with tabs[1]:
        st.dataframe(result.fluid_property_table(), width="stretch")
    with tabs[2]:
        st.dataframe(result.pipe_hydraulics_table(), width="stretch")
    with tabs[3]:
        safety = calculate_safety(result, st.session_state.get("dynamic_profile"))
        st.session_state.safety_result = safety
        st.dataframe(safety.as_dataframe(), width="stretch")
        for rec in safety.recommendations:
            st.caption(f"- {rec}")
    with tabs[4]:
        df = pd.DataFrame(
            {
                "temperature_C": [70, 85, 100, 115, 130],
                "viscosity_proxy": [
                    k["dynamic_viscosity_Pa_s"] * (2.71828 ** (1800.0 / (t + 273.15) - 1800.0 / (config.temperature_C + 273.15)))
                    for t in [70, 85, 100, 115, 130]
                ],
            }
        )
        st.plotly_chart(px.line(df, x="temperature_C", y="viscosity_proxy", markers=True, title="温度 vs 黏度趋势"), width="stretch")

