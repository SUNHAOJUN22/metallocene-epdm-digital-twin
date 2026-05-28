"""Streamlit app for metallocene EPDM/EPM process simulation."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import streamlit as st

from epdm_sim.components import component_dataframe, load_components, solvent_names
from epdm_sim.cfd.mesh import CFDGeometryConfig
from epdm_sim.cfd.openfoam_export import export_openfoam_case_zip
from epdm_sim.cfd.simple_solver import CFDInput, build_cfd_input_from_flowsheet, run_simple_cfd
from epdm_sim.cfd.visualization import (
    contour_plot,
    export_legacy_vtk,
    mesh_plot,
    streamline_plot,
    surface_plot,
    velocity_vector_plot,
)
from epdm_sim.fluid_props import (
    calibrate_viscosity_parameters,
    polymer_solution_viscosity,
)
from epdm_sim.flowsheet import ProcessConfig, load_default_config, run_flowsheet
from epdm_sim.optimizer import optimize_for_grade
from epdm_sim.plotting import (
    composition_bar,
    conversion_bar,
    flash_split_chart,
    flowsheet_block_diagram,
    optimization_convergence,
    property_curve,
    sankey_material,
    sensitivity_heatmap,
    sensitivity_line,
)
from epdm_sim.polymer_props import grade_match, load_target_grades
from epdm_sim.report import export_excel, export_pdf_report, export_word_report
from epdm_sim.sensitivity import (
    TARGET_LABELS,
    VARIABLE_LABELS,
    default_values_for_variable,
    scan_single_variable,
    scan_two_variables,
)
from epdm_sim.utils import data_path, model_dump_compat, write_json


st.set_page_config(
    page_title="茂金属EPDM/EPM工艺仿真MVP",
    page_icon="EPDM",
    layout="wide",
)


ASSUMPTIONS = """
- 这是研发级表观模型，不是工业设计包；
- 动力学参数需要用更多实验数据校准；
- 热力学模型对聚合物溶液、ENB活度和高压气液平衡做了简化；
- 结果用于研发趋势判断、实验设计和工艺窗口筛选。
"""


def init_state() -> None:
    """Initialize Streamlit session state."""
    if "config" not in st.session_state:
        st.session_state.config = model_dump_compat(load_default_config())
    if "sensitivity_df" not in st.session_state:
        st.session_state.sensitivity_df = pd.DataFrame()
    if "optimization" not in st.session_state:
        st.session_state.optimization = None
    if "heat_fluid_curves" not in st.session_state:
        st.session_state.heat_fluid_curves = {}
    if "cfd_result" not in st.session_state:
        st.session_state.cfd_result = None


def current_config() -> ProcessConfig:
    """Return current process config from session state."""
    return ProcessConfig(**st.session_state.config)


def save_config(cfg: ProcessConfig) -> None:
    """Persist process config to session state."""
    st.session_state.config = model_dump_compat(cfg)


def show_assumptions_button() -> None:
    """Show model assumptions as a dialog when supported."""
    if hasattr(st, "dialog"):
        @st.dialog("模型假设说明")
        def _dialog():
            st.markdown(ASSUMPTIONS)

        if st.sidebar.button("模型假设说明"):
            _dialog()
    else:
        with st.sidebar.expander("模型假设说明"):
            st.markdown(ASSUMPTIONS)


def run_current():
    """Run flowsheet for current config."""
    return run_cached_flowsheet(config_cache_key(current_config()))


def config_cache_key(cfg: ProcessConfig) -> str:
    """Return a stable cache key for Streamlit data caching."""
    return json.dumps(model_dump_compat(cfg), sort_keys=True)


@st.cache_data(show_spinner=False)
def run_cached_flowsheet(config_key: str):
    """Run and cache the flowsheet so page rerenders do not recompute it."""
    return run_flowsheet(ProcessConfig(**json.loads(config_key)))


def page_dashboard() -> None:
    """Dashboard page."""
    st.title("茂金属乙丙橡胶 EPDM/EPM 溶液聚合工艺仿真")
    result = run_current()
    for warning in result.warnings:
        st.warning(warning)
    st.caption("流程：Feed -> Mixer -> Preheater -> Reactor(s) -> Quench -> Flash-1 -> Flash-2 -> Product + Recycle")
    k = result.kpis
    cols = st.columns(6)
    cols[0].metric("聚合物 kg/h", f"{k['polymer_kg_h']:.2f}")
    cols[1].metric("C2转化率", f"{k['C2_conversion_pct']:.1f}%")
    cols[2].metric("C3转化率", f"{k['C3_conversion_pct']:.1f}%")
    cols[3].metric("ENB转化率", f"{k['ENB_conversion_pct']:.1f}%")
    cols[4].metric("产品ENB含量", f"{k['ENB_wt']:.2f}%")
    cols[5].metric("门尼估算", f"{k['Mooney']:.1f}")
    cols = st.columns(6)
    cols[0].metric("Mw估算", f"{k['Mw']:.0f}")
    cols[1].metric("PDI", f"{k['PDI']:.2f}")
    cols[2].metric("Tg/Tm", f"{k['Tg_C']:.1f} / {k['Tm_C'] if k['Tm_C'] is not None else '无'}")
    cols[3].metric("挂胶风险", f"{k['fouling_risk']} ({k['fouling_index']:.2f})")
    cols[4].metric("反应热负荷", f"{k['heat_duty_kW']:.2f} kW")
    cols[5].metric("牌号匹配度", f"{k['best_grade']} {k['best_grade_score']:.1f}")
    with st.expander("查看流程图、物料流和组成图", expanded=False):
        st.plotly_chart(flowsheet_block_diagram(), use_container_width=True)
        left, right = st.columns([1.1, 1])
        with left:
            st.subheader("物料流 Sankey")
            st.plotly_chart(sankey_material(result), use_container_width=True)
        with right:
            st.subheader("组成与转化率")
            st.plotly_chart(conversion_bar(result), use_container_width=True)
            st.plotly_chart(composition_bar(result), use_container_width=True)
    st.subheader("工艺优化建议")
    for rec in k["recommendations"]:
        st.write(f"- {rec}")


def page_conditions() -> None:
    """Feed and process condition inputs."""
    st.title("进料与工艺条件")
    cfg = current_config()
    with st.form("conditions_form"):
        c1, c2, c3 = st.columns(3)
        cfg.ethylene_kg_h = c1.number_input("乙烯进料 kg/h", min_value=0.0, value=float(cfg.ethylene_kg_h), step=1.0)
        cfg.propylene_kg_h = c2.number_input("丙烯进料 kg/h", min_value=0.0, value=float(cfg.propylene_kg_h), step=1.0)
        cfg.enb_kg_h = c3.number_input("ENB进料 kg/h", min_value=0.0, value=float(cfg.enb_kg_h), step=0.2)
        c1, c2, c3 = st.columns(3)
        cfg.hydrogen_g_h = c1.number_input("氢气进料 g/h", min_value=0.0, value=float(cfg.hydrogen_g_h), step=0.5)
        cfg.solvent = c2.selectbox("溶剂", solvent_names(), index=solvent_names().index(cfg.solvent) if cfg.solvent in solvent_names() else 0)
        cfg.solvent_mass_kg_h = c3.number_input("溶剂进料 kg/h", min_value=0.0, value=float(cfg.solvent_mass_kg_h), step=5.0)
        c1, c2, c3 = st.columns(3)
        cfg.catalyst_umol_h = c1.number_input("催化剂用量 umol/h", min_value=0.0, value=float(cfg.catalyst_umol_h), step=10.0)
        cfg.AlTi_ratio = c2.number_input("Al/Ti比", min_value=1.0, value=float(cfg.AlTi_ratio), step=50.0)
        cfg.BHT_ratio = c3.number_input("BHT比例", min_value=0.0, value=float(cfg.BHT_ratio), step=0.1)
        c1, c2, c3 = st.columns(3)
        cfg.temperature_C = c1.number_input("反应温度 °C", min_value=40.0, max_value=180.0, value=float(cfg.temperature_C), step=1.0)
        cfg.pressure_MPa = c2.number_input("反应压力 MPa", min_value=0.1, max_value=5.0, value=float(cfg.pressure_MPa), step=0.1)
        cfg.residence_time_min = c3.number_input("停留时间 min", min_value=0.1, value=float(cfg.residence_time_min), step=1.0)
        c1, c2, c3 = st.columns(3)
        cfg.reactor_volume_L = c1.number_input("反应器体积 L", min_value=0.1, value=float(cfg.reactor_volume_L), step=1.0)
        cfg.reactor_mode = c2.selectbox("反应器模式", ["Batch reactor", "CSTR", "CSTR series"], index=["Batch reactor", "CSTR", "CSTR series"].index(cfg.reactor_mode))
        cfg.num_cstr = c3.number_input("串联CSTR数量", min_value=1, max_value=8, value=int(cfg.num_cstr), step=1)
        submitted = st.form_submit_button("更新并计算")
    if submitted:
        save_config(cfg)
        st.success("工况已更新。")
    result = run_current()
    st.dataframe(result.stream_table(), use_container_width=True)


def page_thermo_flash() -> None:
    """Thermodynamics and flash page."""
    st.title("热力学与闪蒸")
    cfg = current_config()
    c1, c2 = st.columns([1, 2])
    with c1:
        cfg.thermo_mode = st.selectbox("热力学模式", ["Simple Wilson K", "thermo package if available"], index=0 if cfg.thermo_mode.startswith("Simple") else 1)
        cfg.flash1_T_C = st.number_input("Flash-1温度 °C", value=float(cfg.flash1_T_C), step=5.0)
        cfg.flash1_P_MPa = st.number_input("Flash-1压力 MPa", value=float(cfg.flash1_P_MPa), step=0.02, min_value=0.001)
        cfg.flash2_T_C = st.number_input("Flash-2温度 °C", value=float(cfg.flash2_T_C), step=5.0)
        cfg.flash2_P_MPa = st.number_input("Flash-2压力 MPa", value=float(cfg.flash2_P_MPa), step=0.005, min_value=0.001)
        cfg.purge_fraction = st.slider("放空气比例", 0.0, 0.5, float(cfg.purge_fraction), 0.01)
        save_config(cfg)
    result = run_current()
    with c2:
        st.info(f"当前热力学模式：{result.kpis['thermo_mode']}")
        st.dataframe(component_dataframe(), use_container_width=True)
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Flash-1 气液分配")
        st.plotly_chart(flash_split_chart(result.flash1), use_container_width=True)
        st.dataframe(result.flash1.split_table, use_container_width=True)
    with c2:
        st.subheader("Flash-2 脱挥分配")
        st.plotly_chart(flash_split_chart(result.flash2), use_container_width=True)
        st.dataframe(result.flash2.split_table, use_container_width=True)
    st.metric("ENB残留", f"{result.kpis['ENB_residue_ppm']:.0f} ppm")
    st.metric("脱挥负荷", f"{result.kpis['devol_duty_kJ_h']:.0f} kJ/h")


def page_reactor() -> None:
    """Reactor detail page."""
    st.title("聚合反应器")
    cfg = current_config()
    with st.expander("夹套/换热器移热能力估算", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        cfg.heat_transfer_U_W_m2K = c1.number_input("U W/m2/K", min_value=1.0, value=float(cfg.heat_transfer_U_W_m2K), step=25.0, key="reactor_U")
        cfg.heat_transfer_area_m2 = c2.number_input("换热面积 A m2", min_value=0.01, value=float(cfg.heat_transfer_area_m2), step=0.1, key="reactor_A")
        cfg.coolant_inlet_C = c3.number_input("冷却介质入口 °C", value=float(cfg.coolant_inlet_C), step=1.0, key="reactor_cin")
        cfg.coolant_outlet_C = c4.number_input("冷却介质出口 °C", value=float(cfg.coolant_outlet_C), step=1.0, key="reactor_cout")
        save_config(cfg)
    result = run_current()
    r = result.reactor
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("r_E mol/L/h", f"{r.rates['r_E']:.4f}")
    c2.metric("r_P mol/L/h", f"{r.rates['r_P']:.4f}")
    c3.metric("r_ENB mol/L/h", f"{r.rates['r_ENB']:.4f}")
    c4.metric("Cstar mol/L", f"{r.Cstar_mol_L:.2e}")
    st.plotly_chart(conversion_bar(result), use_container_width=True)
    st.subheader("沿CSTR串联组成变化")
    st.dataframe(r.stage_dataframe(), use_container_width=True)
    st.metric("聚合热负荷", f"{result.kpis['heat_duty_kW']:.2f} kW")
    c1, c2, c3 = st.columns(3)
    c1.metric("最大可移热能力", f"{result.kpis['Q_max_kW']:.2f} kW")
    c2.metric("移热裕度", f"{result.kpis['cooling_margin_kW']:.2f} kW")
    c3.metric("绝热温升", f"{result.kpis['deltaT_ad_K']:.1f} K")
    if result.kpis["cooling_margin_kW"] < 0:
        st.error("移热能力不足，存在温升和失控风险")
    else:
        st.success("移热能力满足当前反应热负荷。")


def _persist_component_editor(edited: pd.DataFrame) -> None:
    """Persist edited component property table to local JSON and refresh caches."""
    cleaned = edited.where(pd.notnull(edited), None)
    payload = {row["name"]: dict(row) for row in cleaned.to_dict(orient="records") if row.get("name")}
    write_json(data_path("components.json"), payload)
    load_components.cache_clear()
    st.cache_data.clear()


@st.cache_data(show_spinner=False)
def _build_heat_fluid_curves_cached(config_key: str) -> dict[str, pd.DataFrame]:
    """Build cached heat/fluid-property curves for the heat-fluid page."""
    cfg = ProcessConfig(**json.loads(config_key))
    result = run_flowsheet(cfg)
    stream = result.reactor.outlet
    temperatures = np.linspace(max(cfg.temperature_C - 30.0, 40.0), cfg.temperature_C + 40.0, 9)
    temp_df = pd.DataFrame(
        {
            "temperature_C": temperatures,
            "viscosity_Pa_s": [
                polymer_solution_viscosity(stream, float(t) + 273.15, result.kpis["Mw"]) for t in temperatures
            ],
        }
    )
    solids_values = np.linspace(0.0, min(max(result.kpis["solids_wt"] * 2.0, 20.0), 45.0), 9)
    solids_df = pd.DataFrame(
        {
            "solids_wt": solids_values,
            "viscosity_Pa_s": [
                polymer_solution_viscosity(stream, stream.temperature_K, result.kpis["Mw"], solids_wt_override=float(s))
                for s in solids_values
            ],
        }
    )
    mw_values = np.linspace(100000.0, 900000.0, 9)
    mw_df = pd.DataFrame(
        {
            "Mw": mw_values,
            "viscosity_Pa_s": [
                polymer_solution_viscosity(stream, stream.temperature_K, float(mw)) for mw in mw_values
            ],
        }
    )
    heat_rows = []
    for temperature in np.linspace(max(cfg.temperature_C - 20.0, 50.0), cfg.temperature_C + 30.0, 6):
        scan_cfg = ProcessConfig(**model_dump_compat(cfg))
        scan_cfg.temperature_C = float(temperature)
        scan = run_flowsheet(scan_cfg)
        heat_rows.append({"temperature_C": temperature, "Q_rxn_kW": scan.kpis["heat_duty_kW"]})
    tau_rows = []
    for tau in np.linspace(10.0, 90.0, 6):
        scan_cfg = ProcessConfig(**model_dump_compat(cfg))
        scan_cfg.residence_time_min = float(tau)
        scan = run_flowsheet(scan_cfg)
        tau_rows.append({"residence_time_min": tau, "solids_wt": scan.kpis["solids_wt"]})
    pressure_rows = []
    for pressure in np.linspace(0.05, 0.8, 6):
        scan_cfg = ProcessConfig(**model_dump_compat(cfg))
        scan_cfg.flash1_P_MPa = float(pressure)
        scan = run_flowsheet(scan_cfg)
        pressure_rows.append({"flash1_P_MPa": pressure, "flash1_recycle_kg_h": scan.kpis["flash1_recycle_kg_h"]})
    return {
        "temperature_viscosity": temp_df,
        "solids_viscosity": solids_df,
        "mw_viscosity": mw_df,
        "temperature_heat": pd.DataFrame(heat_rows),
        "tau_solids": pd.DataFrame(tau_rows),
        "pressure_recovery": pd.DataFrame(pressure_rows),
    }


def _build_fast_viscosity_curves(cfg: ProcessConfig, result) -> dict[str, pd.DataFrame]:
    """Build fast local viscosity curves without extra flowsheet scans."""
    stream = result.reactor.outlet
    temperatures = np.linspace(max(cfg.temperature_C - 30.0, 40.0), cfg.temperature_C + 40.0, 9)
    solids_values = np.linspace(0.0, min(max(result.kpis["solids_wt"] * 2.0, 20.0), 45.0), 9)
    mw_values = np.linspace(100000.0, 900000.0, 9)
    return {
        "temperature_viscosity": pd.DataFrame(
            {
                "temperature_C": temperatures,
                "viscosity_Pa_s": [
                    polymer_solution_viscosity(stream, float(t) + 273.15, result.kpis["Mw"])
                    for t in temperatures
                ],
            }
        ),
        "solids_viscosity": pd.DataFrame(
            {
                "solids_wt": solids_values,
                "viscosity_Pa_s": [
                    polymer_solution_viscosity(
                        stream,
                        stream.temperature_K,
                        result.kpis["Mw"],
                        solids_wt_override=float(s),
                    )
                    for s in solids_values
                ],
            }
        ),
        "mw_viscosity": pd.DataFrame(
            {
                "Mw": mw_values,
                "viscosity_Pa_s": [
                    polymer_solution_viscosity(stream, stream.temperature_K, float(mw))
                    for mw in mw_values
                ],
            }
        ),
    }


def page_heat_fluid() -> None:
    """Heat balance and fluid-property page."""
    st.title("热量衡算与流体性质")
    cfg = current_config()
    with st.form("heat_fluid_inputs"):
        st.subheader("反应热、传热与管路输入")
        c1, c2, c3 = st.columns(3)
        cfg.deltaH_ethylene_kJ_mol = c1.number_input("乙烯聚合热 kJ/mol", value=float(cfg.deltaH_ethylene_kJ_mol), step=1.0)
        cfg.deltaH_propylene_kJ_mol = c2.number_input("丙烯聚合热 kJ/mol", value=float(cfg.deltaH_propylene_kJ_mol), step=1.0)
        cfg.deltaH_ENB_kJ_mol = c3.number_input("ENB聚合热 kJ/mol", value=float(cfg.deltaH_ENB_kJ_mol), step=1.0)
        c1, c2, c3, c4 = st.columns(4)
        cfg.heat_transfer_U_W_m2K = c1.number_input("总传热系数 U W/m2/K", min_value=1.0, value=float(cfg.heat_transfer_U_W_m2K), step=25.0)
        cfg.heat_transfer_area_m2 = c2.number_input("换热面积 A m2", min_value=0.01, value=float(cfg.heat_transfer_area_m2), step=0.1)
        cfg.coolant_inlet_C = c3.number_input("冷却介质入口温度 °C", value=float(cfg.coolant_inlet_C), step=1.0)
        cfg.coolant_outlet_C = c4.number_input("冷却介质出口温度 °C", value=float(cfg.coolant_outlet_C), step=1.0)
        c1, c2, c3, c4 = st.columns(4)
        cfg.pipe_length_m = c1.number_input("管长 L m", min_value=0.1, value=float(cfg.pipe_length_m), step=1.0)
        cfg.pipe_diameter_m = c2.number_input("管径 D m", min_value=0.001, value=float(cfg.pipe_diameter_m), step=0.001, format="%.4f")
        cfg.pipe_roughness_m = c3.number_input("粗糙度 m", min_value=0.0, value=float(cfg.pipe_roughness_m), step=0.00001, format="%.6f")
        cfg.pump_efficiency = c4.number_input("泵效率", min_value=0.05, max_value=1.0, value=float(cfg.pump_efficiency), step=0.05)
        submitted = st.form_submit_button("更新热量与流体计算")
    if submitted:
        save_config(cfg)
        st.success("热量衡算和流体性质参数已更新。")
    result = run_current()
    k = result.kpis
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("聚合反应热", f"{k['heat_duty_kW']:.2f} kW")
    c2.metric("预热负荷", f"{k['preheat_kW']:.2f} kW")
    c3.metric("脱挥负荷", f"{k['devol_duty_kW']:.2f} kW")
    c4.metric("总冷却负荷", f"{k['total_cooling_load_kW']:.2f} kW")
    c5.metric("绝热温升", f"{k['deltaT_ad_K']:.1f} K")
    c6.metric("热风险等级", str(k["thermal_risk"]))
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("混合物密度", f"{k['liquid_density_kg_m3']:.1f} kg/m3")
    c2.metric("混合物Cp", f"{k['Cp_liq_kJ_kgK']:.3f} kJ/kg/K")
    c3.metric("混合物黏度", f"{k['dynamic_viscosity_Pa_s']:.4g} Pa.s")
    c4.metric("导热系数", f"{k['thermal_conductivity_W_mK']:.3f} W/m/K")
    c5.metric("移热裕度", f"{k['cooling_margin_kW']:.2f} kW")
    c6.metric("泵功率", f"{k['pump_power_kW']:.3f} kW")
    if k["cooling_margin_kW"] < 0:
        st.error("移热能力不足，存在温升和失控风险")
    if k["transport_risk"] != "normal":
        st.warning(k["transport_risk"])
    st.subheader("核心计算表")
    t1, t2, t3 = st.tabs(["热量衡算", "流体性质", "压降与泵送"])
    with t1:
        st.dataframe(result.heat_balance_table(), use_container_width=True)
    with t2:
        st.dataframe(result.fluid_property_table(), use_container_width=True)
        st.caption("物性字段来源为 data/components.json 中的默认工程估算值；可在下方编辑或导入实测数据校准。")
    with t3:
        st.dataframe(result.pipe_hydraulics_table(), use_container_width=True)
    st.subheader("趋势图")
    curves = _build_fast_viscosity_curves(current_config(), result)
    cache_key = config_cache_key(current_config())
    c_scan, c_note = st.columns([1, 3])
    run_scan = c_scan.button("生成/刷新流程扫描曲线")
    c_note.caption("黏度曲线即时计算；反应热、固含和闪蒸回收曲线需要多次流程模拟，点击按钮后生成并缓存，避免页面一直运行。")
    if run_scan:
        with st.spinner("正在计算流程扫描曲线..."):
            st.session_state.heat_fluid_curves = _build_heat_fluid_curves_cached(cache_key)
    scan_curves = st.session_state.heat_fluid_curves if st.session_state.heat_fluid_curves else {}
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(property_curve(curves["temperature_viscosity"], "temperature_C", "viscosity_Pa_s", "温度 vs 黏度", "Pa.s"), use_container_width=True)
        st.plotly_chart(property_curve(curves["mw_viscosity"], "Mw", "viscosity_Pa_s", "Mw vs 黏度", "Pa.s"), use_container_width=True)
        if "tau_solids" in scan_curves:
            st.plotly_chart(property_curve(scan_curves["tau_solids"], "residence_time_min", "solids_wt", "停留时间 vs 固含量", "wt%"), use_container_width=True)
    with c2:
        st.plotly_chart(property_curve(curves["solids_viscosity"], "solids_wt", "viscosity_Pa_s", "固含量 vs 黏度", "Pa.s"), use_container_width=True)
        if "temperature_heat" in scan_curves:
            st.plotly_chart(property_curve(scan_curves["temperature_heat"], "temperature_C", "Q_rxn_kW", "反应温度 vs 反应热负荷", "kW"), use_container_width=True)
        if "pressure_recovery" in scan_curves:
            st.plotly_chart(property_curve(scan_curves["pressure_recovery"], "flash1_P_MPa", "flash1_recycle_kg_h", "压力 vs 闪蒸回收率", "kg/h"), use_container_width=True)
    st.subheader("默认估算物性与校准数据")
    with st.expander("编辑组件流体物性"):
        edited = st.data_editor(component_dataframe(), use_container_width=True, num_rows="fixed")
        if st.button("应用物性修改到本地 components.json"):
            _persist_component_editor(edited)
            st.success("物性数据已更新。页面重新运行后使用新物性。")
    with st.expander("导入流体性质校准数据 CSV"):
        st.write("字段：temperature_C, solids_wt, Mw, viscosity_Pa_s, density_kg_m3, Cp_kJ_kgK")
        uploaded = st.file_uploader("导入实测流体性质数据", type=["csv"])
        if uploaded is not None and st.button("保存并重新拟合黏度模型"):
            data_path("fluid_property_calibration.csv").write_bytes(uploaded.getvalue())
            calibrate_viscosity_parameters.cache_clear()
            st.success("校准数据已保存，黏度模型参数将在后续计算中更新。")


def page_product() -> None:
    """Product property page."""
    st.title("产品性能预测")
    result = run_current()
    k = result.kpis
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("产品乙烯含量", f"{k['C2_wt']:.2f}%")
    c2.metric("产品ENB含量", f"{k['ENB_wt']:.2f}%")
    c3.metric("门尼估算", f"{k['Mooney']:.1f}")
    c4.metric("挂胶风险", f"{k['fouling_risk']} ({k['fouling_index']:.2f})")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Mw", f"{k['Mw']:.0f}")
    c2.metric("Mn", f"{k['Mn']:.0f}")
    c3.metric("PDI", f"{k['PDI']:.2f}")
    c4.metric("Tg / Tm", f"{k['Tg_C']:.1f} / {k['Tm_C'] if k['Tm_C'] is not None else '无'}")
    st.plotly_chart(composition_bar(result), use_container_width=True)
    grades = load_target_grades()
    grade_id = st.selectbox("目标牌号", list(grades.keys()), index=list(grades.keys()).index(k["best_grade"]) if k["best_grade"] in grades else 0)
    match = grade_match(k, grade_id)
    st.metric("牌号匹配度", f"{match['score']:.1f}")
    st.json(match["grade"], expanded=False)


def page_cfd() -> None:
    """CFD/FEM-style visualization page."""
    st.title("CFD有限元流场仿真")
    st.warning(
        "本CFD模块为研发级二维/准三维可视化模型，用于判断趋势、热点、混合死区、黏度场和挂胶风险。"
        "工业设计必须使用实验流变数据、真实几何、真实搅拌桨、湍流模型和OpenFOAM/Fluent等专业CFD验证。"
    )
    flowsheet_result = run_current()
    default_cfd = build_cfd_input_from_flowsheet(flowsheet_result)
    with st.form("cfd_inputs"):
        st.subheader("几何与网格")
        c1, c2, c3, c4 = st.columns(4)
        solver_mode = c1.selectbox("求解模式", ["Simple CFD", "FEniCSx FEM"], index=0)
        geometry_type = c2.selectbox("几何模板", ["Pipe 2D", "Reactor cross-section", "Annulus"], index=1)
        grid = c3.selectbox("网格", ["40x20", "80x40", "120x60"], index=1)
        agitation_rpm = c4.number_input("搅拌转速 rpm", min_value=0.0, value=float(default_cfd.agitation_rpm), step=50.0)
        nx, ny = [int(value) for value in grid.split("x")]
        c1, c2, c3, c4 = st.columns(4)
        pipe_length = c1.number_input("管长 m", min_value=0.1, value=float(default_cfd.geometry.pipe_length_m), step=1.0)
        pipe_diameter = c2.number_input("管径 m", min_value=0.001, value=float(default_cfd.geometry.pipe_diameter_m), step=0.001, format="%.4f")
        reactor_diameter = c3.number_input("反应釜直径 m", min_value=0.05, value=float(default_cfd.geometry.reactor_diameter_m), step=0.02)
        impeller_diameter = c4.number_input("桨径 m", min_value=0.01, value=float(default_cfd.geometry.impeller_diameter_m), step=0.01)
        st.subheader("流体性质")
        c1, c2, c3, c4 = st.columns(4)
        density = c1.number_input("密度 kg/m3", min_value=1.0, value=float(default_cfd.density_kg_m3), step=10.0)
        viscosity = c2.number_input("黏度 Pa.s", min_value=1.0e-8, value=float(default_cfd.viscosity_Pa_s), step=1.0e-4, format="%.6g")
        cp = c3.number_input("Cp kJ/kg/K", min_value=0.1, value=float(default_cfd.Cp_kJ_kgK), step=0.05)
        conductivity = c4.number_input("导热系数 W/m/K", min_value=0.01, value=float(default_cfd.thermal_conductivity_W_mK), step=0.01)
        c1, c2, c3 = st.columns(3)
        d_e = c1.number_input("D_E m2/s", min_value=1.0e-12, value=float(default_cfd.diffusivity_E_m2_s), format="%.2e")
        d_p = c2.number_input("D_P m2/s", min_value=1.0e-12, value=float(default_cfd.diffusivity_P_m2_s), format="%.2e")
        d_enb = c3.number_input("D_ENB m2/s", min_value=1.0e-12, value=float(default_cfd.diffusivity_ENB_m2_s), format="%.2e")
        st.subheader("反应热源与边界条件")
        c1, c2, c3, c4 = st.columns(4)
        heat_generation = c1.number_input("热源 W/m3", min_value=0.0, value=float(default_cfd.heat_generation_W_m3), step=1000.0)
        inlet_velocity = c2.number_input("入口速度 m/s", min_value=0.0, value=float(default_cfd.inlet_velocity_m_s), step=0.02)
        inlet_temp = c3.number_input("入口温度 °C", value=float(default_cfd.inlet_temperature_C), step=1.0)
        wall_temp = c4.number_input("壁面/冷却温度 °C", value=float(default_cfd.wall_temperature_C), step=1.0)
        c1, c2, c3, c4 = st.columns(4)
        c_e = c1.number_input("入口C_E mol/m3", min_value=0.0, value=float(default_cfd.inlet_C_E_mol_m3), step=100.0)
        c_p = c2.number_input("入口C_P mol/m3", min_value=0.0, value=float(default_cfd.inlet_C_P_mol_m3), step=100.0)
        c_enb = c3.number_input("入口C_ENB mol/m3", min_value=0.0, value=float(default_cfd.inlet_C_ENB_mol_m3), step=10.0)
        outlet_p = c4.number_input("出口压力 Pa", min_value=0.0, value=float(default_cfd.outlet_pressure_Pa), step=1000.0)
        run_cfd = st.form_submit_button("运行CFD", type="primary")
    cfd_input = CFDInput(
        solver_mode=solver_mode,
        geometry=CFDGeometryConfig(
            geometry_type=geometry_type,
            nx=nx,
            ny=ny,
            pipe_length_m=pipe_length,
            pipe_diameter_m=pipe_diameter,
            reactor_diameter_m=reactor_diameter,
            impeller_diameter_m=impeller_diameter,
        ),
        density_kg_m3=density,
        viscosity_Pa_s=viscosity,
        Cp_kJ_kgK=cp,
        thermal_conductivity_W_mK=conductivity,
        diffusivity_E_m2_s=d_e,
        diffusivity_P_m2_s=d_p,
        diffusivity_ENB_m2_s=d_enb,
        heat_generation_W_m3=heat_generation,
        r_E_mol_m3_s=default_cfd.r_E_mol_m3_s,
        r_P_mol_m3_s=default_cfd.r_P_mol_m3_s,
        r_ENB_mol_m3_s=default_cfd.r_ENB_mol_m3_s,
        polymer_generation_rate_kg_m3_s=default_cfd.polymer_generation_rate_kg_m3_s,
        inlet_velocity_m_s=inlet_velocity,
        inlet_temperature_C=inlet_temp,
        wall_temperature_C=wall_temp,
        coolant_temperature_C=wall_temp,
        inlet_C_E_mol_m3=c_e,
        inlet_C_P_mol_m3=c_p,
        inlet_C_ENB_mol_m3=c_enb,
        outlet_pressure_Pa=outlet_p,
        pressure_Pa=default_cfd.pressure_Pa,
        solids_wt=flowsheet_result.kpis["solids_wt"],
        Mw=flowsheet_result.kpis["Mw"],
        PDI=flowsheet_result.kpis["PDI"],
        agitation_rpm=agitation_rpm,
        overall_U_W_m2K=flowsheet_result.config.heat_transfer_U_W_m2K,
        cooling_duty_kW=flowsheet_result.kpis["total_cooling_load_kW"],
        residence_time_s=flowsheet_result.config.residence_time_min * 60.0,
    )
    if run_cfd or st.session_state.cfd_result is None:
        with st.spinner("正在运行二维/准三维CFD可视化模型..."):
            st.session_state.cfd_result = run_simple_cfd(cfd_input)
    cfd_result = st.session_state.cfd_result
    for warning in cfd_result.warnings:
        st.warning(warning)
    d = cfd_result.diagnostics
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("当前模式", cfd_result.mode)
    c2.metric("平均速度", f"{d.average_velocity_m_s:.3f} m/s")
    c3.metric("Re", f"{d.Reynolds:.0f}")
    c4.metric("压降", f"{d.pressure_drop_Pa / 1000.0:.2f} kPa")
    c5.metric("最大温度", f"{d.max_temperature_C:.1f} °C")
    c6.metric("死区比例", f"{100.0 * d.dead_zone_fraction:.1f}%")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("混合均匀性指数", f"{d.mixing_index:.3f}")
    c2.metric("壁面最大挂胶风险", f"{d.wall_max_fouling_risk:.2f}")
    c3.metric("修正U", f"{d.corrected_heat_transfer_U_W_m2K:.0f} W/m2/K")
    c4.metric("建议搅拌转速", f"{d.suggested_agitation_rpm:.0f} rpm")
    c5.metric("推荐冷却负荷", f"{d.recommended_cooling_duty_kW:.2f} kW")
    st.subheader("结果云图")
    tabs = st.tabs(["网格/速度/流线", "温度/ENB/固含", "黏度/挂胶/压力", "准三维", "工程诊断", "导出"])
    with tabs[0]:
        c1, c2 = st.columns(2)
        c1.plotly_chart(mesh_plot(cfd_result), use_container_width=True)
        c2.plotly_chart(velocity_vector_plot(cfd_result), use_container_width=True)
        st.plotly_chart(streamline_plot(cfd_result), use_container_width=True)
    with tabs[1]:
        c1, c2, c3 = st.columns(3)
        c1.plotly_chart(contour_plot(cfd_result, "temperature"), use_container_width=True)
        c2.plotly_chart(contour_plot(cfd_result, "ENB"), use_container_width=True)
        c3.plotly_chart(contour_plot(cfd_result, "solids"), use_container_width=True)
    with tabs[2]:
        c1, c2, c3 = st.columns(3)
        c1.plotly_chart(contour_plot(cfd_result, "viscosity"), use_container_width=True)
        c2.plotly_chart(contour_plot(cfd_result, "fouling"), use_container_width=True)
        c3.plotly_chart(contour_plot(cfd_result, "pressure"), use_container_width=True)
    with tabs[3]:
        field = st.selectbox("准三维字段", ["temperature", "viscosity", "fouling", "ENB"], index=0)
        st.plotly_chart(surface_plot(cfd_result, field), use_container_width=True)
    with tabs[4]:
        st.dataframe(d.as_dataframe(), use_container_width=True)
        st.subheader("工程建议")
        for rec in d.recommendations:
            st.write(f"- {rec}")
        st.subheader("反馈给主流程的诊断量")
        st.write(f"- corrected heat transfer coefficient: {d.corrected_heat_transfer_U_W_m2K:.1f} W/m2/K")
        st.write(f"- CFD fouling risk: {d.wall_max_fouling_risk:.2f}")
        st.write(f"- dead zone fraction: {d.dead_zone_fraction:.3f}")
        st.write(f"- suggested max solids content: {d.suggested_max_solids_wt:.1f} wt%")
        st.write(f"- recommended cooling duty: {d.recommended_cooling_duty_kW:.2f} kW")
    with tabs[5]:
        st.download_button(
            "导出 VTK 文件",
            data=export_legacy_vtk(cfd_result),
            file_name="epdm_cfd_fields.vtk",
            mime="application/octet-stream",
        )
        st.download_button(
            "下载 OpenFOAM Case",
            data=export_openfoam_case_zip(cfd_result.input),
            file_name="epdm_openfoam_case.zip",
            mime="application/zip",
        )


def page_sensitivity() -> None:
    """Sensitivity analysis page."""
    st.title("敏感性分析")
    cfg = current_config()
    c1, c2, c3 = st.columns(3)
    variable = c1.selectbox("扫描变量", list(VARIABLE_LABELS.keys()))
    target = c2.selectbox("显示目标", list(TARGET_LABELS.keys()))
    points = c3.slider("扫描点数", 5, 21, 9, 2)
    y_map = {
        "maximize ENB wt%": "ENB_wt",
        "minimize ENB residue": "ENB_residue_ppm",
        "target Mooney": "Mooney",
        "target C2 wt%": "C2_wt",
        "minimize fouling": "fouling_index",
        "maximize productivity": "productivity",
    }
    if st.button("运行单变量扫描", type="primary"):
        values = default_values_for_variable(cfg, variable, points)
        st.session_state.sensitivity_df = scan_single_variable(cfg, variable, values)
    df = st.session_state.sensitivity_df
    if not df.empty:
        st.plotly_chart(sensitivity_line(df, y_map[target]), use_container_width=True)
        st.dataframe(df, use_container_width=True)
    st.divider()
    st.subheader("双变量热图")
    c1, c2, c3 = st.columns(3)
    var_x = c1.selectbox("X变量", list(VARIABLE_LABELS.keys()), index=1)
    var_y = c2.selectbox("Y变量", list(VARIABLE_LABELS.keys()), index=2)
    heat_target = c3.selectbox("热图目标", ["ENB_wt", "Mooney", "C2_wt", "fouling_index", "heat_duty_kW"])
    if st.button("运行双变量扫描"):
        values_x = default_values_for_variable(cfg, var_x, 7)
        values_y = default_values_for_variable(cfg, var_y, 7)
        heat_df = scan_two_variables(cfg, var_x, values_x, var_y, values_y)
        st.session_state.sensitivity_df = heat_df
        st.plotly_chart(sensitivity_heatmap(heat_df, var_x, var_y, heat_target), use_container_width=True)
        st.dataframe(heat_df, use_container_width=True)


def page_optimizer() -> None:
    """Optimizer page."""
    st.title("优化器")
    cfg = current_config()
    grades = load_target_grades()
    c1, c2, c3 = st.columns(3)
    grade_id = c1.selectbox("目标牌号", list(grades.keys()))
    maxiter = c2.slider("优化迭代上限", 5, 50, 15, 5)
    residue_limit = c3.number_input("ENB残留上限 ppm", min_value=1000.0, value=80000.0, step=5000.0)
    st.json(grades[grade_id], expanded=False)
    if st.button("开始优化", type="primary"):
        with st.spinner("正在优化工艺窗口..."):
            st.session_state.optimization = optimize_for_grade(cfg, grade_id, maxiter=maxiter, enb_residue_threshold_ppm=residue_limit)
    opt = st.session_state.optimization
    if opt is not None:
        c1, c2, c3 = st.columns(3)
        c1.metric("匹配分数", f"{opt.score:.1f}")
        c2.metric("可行性", "可行" if opt.feasible else "需人工复核")
        c3.metric("目标函数", f"{opt.objective:.3f}")
        st.plotly_chart(optimization_convergence(opt.history), use_container_width=True)
        st.subheader("推荐工艺窗口")
        st.dataframe(pd.DataFrame([model_dump_compat(opt.config)]), use_container_width=True)
        st.subheader("优化结果KPI")
        st.dataframe(pd.DataFrame([opt.kpis]).drop(columns=["recommendations"], errors="ignore"), use_container_width=True)
        if st.button("应用推荐工况"):
            save_config(opt.config)
            st.success("推荐工况已应用到当前配置。")


def page_report() -> None:
    """Report export page."""
    st.title("报告导出")
    result = run_current()
    sensitivity_df = st.session_state.sensitivity_df
    optimization = st.session_state.optimization
    st.subheader("导出内容预览")
    st.dataframe(result.stream_table(), use_container_width=True)
    excel_bytes = export_excel(result, sensitivity_df=sensitivity_df, optimization=optimization)
    pdf_bytes = export_pdf_report(result, sensitivity_df=sensitivity_df, optimization=optimization)
    word_bytes = export_word_report(result, sensitivity_df=sensitivity_df, optimization=optimization)
    c1, c2, c3 = st.columns(3)
    c1.download_button(
        "导出 Excel",
        data=excel_bytes,
        file_name="epdm_process_simulation.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    c2.download_button(
        "导出 PDF 报告",
        data=pdf_bytes,
        file_name="epdm_process_simulation_report.pdf",
        mime="application/pdf",
    )
    c3.download_button(
        "导出 Word 报告",
        data=word_bytes,
        file_name="epdm_process_simulation_report.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


def main() -> None:
    """Application entrypoint."""
    init_state()
    st.sidebar.title("EPDM工艺仿真")
    pages = {
        "首页 Dashboard": page_dashboard,
        "进料与工艺条件": page_conditions,
        "热力学与闪蒸": page_thermo_flash,
        "聚合反应器": page_reactor,
        "热量衡算与流体性质": page_heat_fluid,
        "CFD有限元流场仿真": page_cfd,
        "产品性能预测": page_product,
        "敏感性分析": page_sensitivity,
        "优化器": page_optimizer,
        "报告导出": page_report,
    }
    page = st.sidebar.radio("页面", list(pages.keys()))
    show_assumptions_button()
    st.sidebar.caption("研发级表观模型，用于趋势判断和实验设计。")
    pages[page]()


if __name__ == "__main__":
    main()
