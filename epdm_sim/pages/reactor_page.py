"""Reactor and kinetics page."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from epdm_sim.plotting import conversion_bar
from epdm_sim.solubility import gas_liquid_saturation_table, gas_mole_fractions_from_feeds
from epdm_sim.ui_theme import kpi_grid, section_title


def render_reactor_page(config, result, save_config_callback=None, store=None) -> None:
    """Render reactor, kinetics and gas-liquid concentration diagnostics."""
    section_title("反应器与动力学")
    k = result.kpis
    rates = result.reactor.rates or {}
    kpi_grid(
        [
            ("rE", f"{float(rates.get('r_E', 0.0)):.3g}", "mol/L/h", "#22d3ee"),
            ("rP", f"{float(rates.get('r_P', 0.0)):.3g}", "mol/L/h", "#22c55e"),
            ("rENB", f"{float(rates.get('r_ENB', 0.0)):.3g}", "mol/L/h", "#f97316"),
            ("Cstar", f"{result.reactor.Cstar_mol_L:.3g}", "mol/L", "#a78bfa"),
            ("生产率", f"{k['catalyst_productivity_g_mol_h']:.2g}", "g/mol/h", "#f59e0b"),
        ]
    )
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(conversion_bar(result), width="stretch")
        st.dataframe(result.reactor.stage_dataframe(), width="stretch", height=320)
    with c2:
        y = gas_mole_fractions_from_feeds(config.ethylene_kg_h, config.propylene_kg_h, config.hydrogen_g_h)
        table = gas_liquid_saturation_table(config.temperature_C + 273.15, config.pressure_MPa, y, config.solvent)
        st.subheader("Henry液相饱和浓度")
        st.dataframe(table, width="stretch")
        comp = pd.DataFrame(
            [{"segment": "ethylene", "wt%": k["C2_wt"]}, {"segment": "propylene", "wt%": k["C3_wt"]}, {"segment": "ENB", "wt%": k["ENB_wt"]}]
        )
        st.plotly_chart(px.bar(comp, x="segment", y="wt%", color="segment", text_auto=".1f"), width="stretch")

