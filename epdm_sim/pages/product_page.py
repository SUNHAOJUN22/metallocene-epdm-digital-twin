"""Product properties and target-grade matching page."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from epdm_sim.polymer_props import grade_match, load_target_grades
from epdm_sim.ui_theme import kpi_grid, section_title


def _fmt_optional(value, digits: int = 1, empty: str = "无峰") -> str:
    """Format optional numeric KPI values without crashing on qualitative results."""
    if value is None:
        return empty
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return empty


def render_product_page(config, result, save_config_callback=None, store=None) -> None:
    """Render product-property prediction and Vistalon-like benchmarking."""
    k = result.kpis
    section_title("产品性能与美孚Vistalon-like对标")
    tg_tm_text = f"{_fmt_optional(k.get('Tg_C'), 1, '-')}/{_fmt_optional(k.get('Tm_C'), 1, '无熔融峰')}"
    kpi_grid(
        [
            ("C2/C3/ENB", f"{k['C2_wt']:.1f}/{k['C3_wt']:.1f}/{k['ENB_wt']:.1f}", "wt%", "#22d3ee"),
            ("Mw/Mn/PDI", f"{k['Mw']:.0f}/{k['Mn']:.0f}/{k['PDI']:.2f}", "estimate", "#a78bfa"),
            ("门尼", f"{k['Mooney']:.1f}", "ML(1+4)", "#f59e0b"),
            ("Tg/Tm", tg_tm_text, "°C", "#60a5fa"),
            ("结晶风险", str(k["crystallinity"]), "qualitative", "#fb923c"),
            ("最佳牌号", str(k["best_grade"]), f"score {k['best_grade_score']:.1f}", "#22c55e"),
        ]
    )
    grades = load_target_grades()
    rows = []
    for grade in grades:
        match = grade_match(k, grade)
        rows.append(match)
    df = pd.DataFrame(rows).sort_values("score", ascending=False)
    c1, c2 = st.columns([1.15, 1.0])
    with c1:
        st.dataframe(df, width="stretch", height=380)
    with c2:
        st.plotly_chart(px.bar(df.head(8), x="grade_id", y="score", color="score", title="牌号匹配度"), width="stretch")
        comp = pd.DataFrame([{"segment": "C2", "wt": k["C2_wt"]}, {"segment": "C3", "wt": k["C3_wt"]}, {"segment": "ENB", "wt": k["ENB_wt"]}])
        st.plotly_chart(px.pie(comp, values="wt", names="segment", hole=0.52, title="产品组成"), width="stretch")

