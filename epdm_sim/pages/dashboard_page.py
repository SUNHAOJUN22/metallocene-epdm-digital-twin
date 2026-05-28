"""Digital-twin dashboard page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from epdm_sim.digital_twin_3d import available_view_modes, build_digital_twin_figure
from epdm_sim.plotting import sankey_material
from epdm_sim.ui_theme import kpi_grid, risk_chip, section_title


def render_dashboard_page(config, result, save_config_callback=None, store=None) -> None:
    """Render the fast digital-twin overview without heavy recomputation."""
    k = result.kpis
    left, center, right = st.columns([0.95, 2.2, 1.05], gap="large")
    with left:
        section_title("快速工艺条件")
        st.metric("反应温度", f"{config.temperature_C:.1f} °C")
        st.metric("反应压力", f"{config.pressure_MPa:.2f} MPa")
        st.metric("ENB进料", f"{config.enb_kg_h:.2f} kg/h")
        st.metric("参数集", config.parameter_set_id)
        if save_config_callback is not None:
            with st.form("dashboard_quick_form"):
                config.temperature_C = st.number_input("反应温度 °C", 60.0, 180.0, float(config.temperature_C), 1.0)
                config.pressure_MPa = st.number_input("反应压力 MPa", 0.1, 5.0, float(config.pressure_MPa), 0.05)
                config.enb_kg_h = st.number_input("ENB kg/h", 0.0, 50.0, float(config.enb_kg_h), 0.1)
                if st.form_submit_button("更新快速配置", type="primary"):
                    save_config_callback(config)
                    st.rerun()
    with center:
        section_title("3D装置总览")
        view_mode = st.radio("视图模式", available_view_modes(), index=0, horizontal=True)
        fig = build_digital_twin_figure(result, mode=view_mode or "物料流模式")
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    with right:
        section_title("工程诊断")
        chips = [
            risk_chip("热风险", str(k.get("thermal_risk"))),
            risk_chip("挂胶风险", str(k.get("fouling_risk"))),
            risk_chip("移热裕度", "不足" if k.get("cooling_margin_kW", 0) < 0 else "正常"),
        ]
        st.markdown(" ".join(chips), unsafe_allow_html=True)
        st.metric("最佳牌号", k.get("best_grade", "-"), f"score {k.get('best_grade_score', 0):.1f}")
        st.metric("ENB残留", f"{k.get('ENB_residue_ppm', 0):.0f} ppm")
        st.metric("回收闭合误差", f"{k.get('recycle_closure_error', 0):.3g} kg/h")
        st.write("建议")
        for rec in k.get("recommendations", [])[:6]:
            st.caption(f"- {rec}")

    kpi_grid(
        [
            ("聚合物产率", f"{k['polymer_kg_h']:.2f} kg/h", "Polymer", "#22d3ee"),
            ("C2 / ENB", f"{k['C2_wt']:.1f}% / {k['ENB_wt']:.1f}%", "product wt%", "#60a5fa"),
            ("Mw / PDI", f"{k['Mw']:.0f} / {k['PDI']:.2f}", "GPC estimate", "#a78bfa"),
            ("门尼估算", f"{k['Mooney']:.1f}", "ML(1+4)", "#f59e0b"),
            ("反应热", f"{k['heat_duty_kW']:.2f} kW", f"ΔTad {k['deltaT_ad_K']:.1f} K", "#ef4444"),
            ("黏度", f"{k['dynamic_viscosity_Pa_s']:.3g} Pa.s", f"ΔP {k['pipe_pressure_drop_kPa']:.1f} kPa", "#a78bfa"),
        ]
    )
    bottom1, bottom2 = st.columns([1.2, 1.0])
    with bottom1:
        section_title("物料衡算 Sankey")
        st.plotly_chart(sankey_material(result), width="stretch")
    with bottom2:
        section_title("关键KPI摘要")
        summary = pd.DataFrame([k]).drop(columns=["recommendations"], errors="ignore").T.reset_index()
        summary.columns = ["KPI", "value"]
        summary["value"] = summary["value"].map(lambda value: "-" if value is None else str(value))
        st.dataframe(summary.head(24), width="stretch", height=360)

