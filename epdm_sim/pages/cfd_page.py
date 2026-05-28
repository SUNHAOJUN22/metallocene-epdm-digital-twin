"""CFD/FEM-style visualization page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from epdm_sim.cfd.mesh import CFDGeometryConfig
from epdm_sim.cfd.openfoam_export import export_openfoam_case_zip
from epdm_sim.cfd.simple_solver import build_cfd_input_from_flowsheet, run_simple_cfd
from epdm_sim.cfd.visualization import contour_plot, export_legacy_vtk, reactor_cfd_3d_view, streamline_plot, velocity_vector_plot
from epdm_sim.services.cache_keys import detail_cache_key
from epdm_sim.ui_theme import kpi_grid, section_title


def render_cfd_page(config, result, save_config_callback=None, store=None) -> None:
    """Render manually triggered CFD-style fields and diagnostics."""
    section_title("CFD有限元风格可视化")
    c1, c2, c3 = st.columns(3)
    geometry = c1.selectbox("几何", ["Reactor cross-section", "Pipe 2D", "Annulus"])
    nx = c2.selectbox("网格", [40, 80, 120], index=1)
    time_min = c3.slider("准动态时间 min", 0, 30, 30)
    c4, c5, c6 = st.columns(3)
    impeller = c4.selectbox("桨型", ["Rushton turbine", "pitched blade turbine", "anchor impeller", "helical ribbon for high viscosity", "simple disk turbine"], index=1)
    baffles = c5.toggle("挡板", value=True)
    feed_pos = c6.selectbox("进料位置", ["top", "side", "near impeller", "bottom"], index=2)
    if st.button("运行详细CFD", type="primary"):
        cfd_input = build_cfd_input_from_flowsheet(result, geometry_type=geometry, nx=int(nx), ny=max(int(nx) // 2, 16))
        cfd_input.dynamic_time_min = float(time_min)
        cfd_input.impeller_type = impeller
        cfd_input.baffles_enabled = bool(baffles)
        cfd_input.feed_position = feed_pos
        cfd_input.geometry.geometry_type = geometry
        key = detail_cache_key(config, {"cfd": cfd_input.model_dump() if hasattr(cfd_input, "model_dump") else cfd_input.dict()})
        with st.spinner("运行轻量CFD场计算..."):
            cfd_result = run_simple_cfd(cfd_input)
            st.session_state.cfd_result = cfd_result
            if store is not None:
                store.cfd_key = key
                store.cfd = cfd_result
    cfd_result = st.session_state.get("cfd_result")
    if cfd_result is None:
        st.info("CFD需要手动运行；默认不会随工艺滑块自动重算。")
        return
    d = cfd_result.diagnostics
    kpi_grid(
        [
            ("Re", f"{d.Reynolds:.0f}", "flow", "#22d3ee"),
            ("死区比例", f"{d.dead_zone_fraction:.2%}", "low velocity", "#f59e0b"),
            ("混合指数", f"{d.mixing_index:.3f}", "ENB std/mean", "#a78bfa"),
            ("高挂胶面积", f"{d.high_fouling_zone_area_fraction:.2%}", "area", "#ef4444"),
            ("低剪切面积", f"{d.low_shear_area_fraction:.2%}", "area", "#fb923c"),
            ("压降/泵功", f"{d.pressure_drop_Pa/1000:.2f}/{d.pump_power_kW:.3f}", "kPa/kW", "#60a5fa"),
        ]
    )
    tabs = st.tabs(["3D剖面", "速度/流线", "温度/浓度", "黏度/挂胶", "诊断与导出"])
    with tabs[0]:
        st.plotly_chart(reactor_cfd_3d_view(cfd_result, "temperature"), width="stretch")
    with tabs[1]:
        st.plotly_chart(velocity_vector_plot(cfd_result), width="stretch")
        st.plotly_chart(streamline_plot(cfd_result), width="stretch")
    with tabs[2]:
        c1, c2 = st.columns(2)
        c1.plotly_chart(contour_plot(cfd_result, "temperature"), width="stretch")
        c2.plotly_chart(contour_plot(cfd_result, "ENB"), width="stretch")
    with tabs[3]:
        c1, c2 = st.columns(2)
        c1.plotly_chart(contour_plot(cfd_result, "viscosity"), width="stretch")
        c2.plotly_chart(contour_plot(cfd_result, "fouling"), width="stretch")
    with tabs[4]:
        st.dataframe(d.as_dataframe(), width="stretch")
        if d.wall_shear_histogram:
            st.dataframe(pd.DataFrame(d.wall_shear_histogram), width="stretch")
        for rec in d.recommendations:
            st.caption(f"- {rec}")
        st.download_button("下载VTK", export_legacy_vtk(cfd_result), "epdm_cfd_fields.vtk")
        st.download_button("下载OpenFOAM Case Zip", export_openfoam_case_zip(cfd_result.input), "epdm_openfoam_case.zip")


