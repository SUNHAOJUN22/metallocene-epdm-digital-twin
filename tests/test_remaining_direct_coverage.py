import json
import math
from types import SimpleNamespace

import pandas as pd

from epdm_sim.components import Component, component_dataframe, get_component, load_components, solvent_names
from epdm_sim.heat_balance import (
    HeatBalanceConfig,
    calculate_heat_balance,
    calculate_lmtd,
    calculate_reaction_heat,
    heat_transfer_capacity_kW,
    thermal_risk_level,
)
from epdm_sim.plot_validation import validate_nonempty_figure
from epdm_sim.plotting import (
    flash_split_chart,
    optimization_convergence,
    property_curve,
    sensitivity_heatmap,
    sensitivity_line,
)
from epdm_sim.polymer_props import (
    calibrate_enb_feed_relationship,
    calibrate_mooney_coefficients,
    estimate_mooney,
    estimate_tg,
    estimate_tm_and_crystallinity,
    fouling_risk_index,
    generate_recommendations,
    grade_bounds,
    grade_match,
    grade_target_value,
    load_internal_experiments,
    load_target_grades,
)
from epdm_sim.reaction_templates import (
    default_epdm_template,
    get_reaction_template,
    heat_balance_deltaH_from_template,
    load_reaction_templates,
    molecular_weights_from_template,
    monomers_from_template,
    property_model_from_template,
    segment_map_from_template,
    template_with_fallback,
    templates_dataframe,
)
from epdm_sim.ui_theme import apply_theme, install_safe_alerts, kpi_grid, section_title, top_bar
from epdm_sim.utils import load_json, load_yaml, mid_range, model_dump_compat, positive, write_json


def test_utils_file_and_model_helpers(tmp_path):
    payload = {"a": 1, "b": [2, 3]}
    path = tmp_path / "payload.json"
    write_json(path, payload)
    assert load_json(path) == payload
    yaml_path = tmp_path / "payload.yaml"
    yaml_path.write_text("x: 2\ny: ok\n", encoding="utf-8")
    assert load_yaml(yaml_path)["x"] == 2
    assert positive(-3.0, floor=0.25) == 0.25
    assert mid_range(2.0, 6.0) == 4.0
    assert model_dump_compat(Component(name="x", formula="X", MW=10, Tc=300, Pc=1e6, omega=0.1, Tb=250, Cp_liq=2, Cp_gas=1, density_liq=700))["name"] == "x"


def test_components_public_loaders_have_physical_units():
    components = load_components()
    assert "ethylene" in components
    ethylene = get_component("ethylene")
    assert isinstance(ethylene, Component)
    assert ethylene.MW > 0
    assert ethylene.mw_kg_per_mol == ethylene.MW / 1000.0
    df = component_dataframe()
    assert not df.empty
    assert (df["MW"] > 0).all()
    solvents = solvent_names()
    assert {"hexane", "heptane", "toluene"}.intersection(solvents)


def test_reaction_template_public_helpers_are_consistent():
    templates = load_reaction_templates()
    assert "EPDM_EPM_metallocene_solution" in templates
    template = get_reaction_template("EPDM_EPM_metallocene_solution")
    assert template == default_epdm_template()
    assert monomers_from_template(template.template_id) == tuple(template.monomers)
    assert segment_map_from_template(template.template_id)["ethylene"] == "E"
    mw = molecular_weights_from_template(template.template_id)
    assert all(value > 0 for value in mw.values())
    delta_h = heat_balance_deltaH_from_template(template.template_id)
    assert all(value < 0 for value in delta_h.values())
    prop_model = property_model_from_template(template.template_id)
    assert prop_model["model_id"]
    fallback, warnings = template_with_fallback("missing_template")
    assert fallback.template_id == "EPDM_EPM_metallocene_solution"
    assert warnings
    assert not templates_dataframe(templates).empty


def test_polymer_property_helpers_have_bounded_outputs():
    experiments = load_internal_experiments()
    assert not experiments.empty
    grades = load_target_grades()
    grade = grades["Vistalon_6602_like"]
    assert grade_target_value(grade, "C2") > 0
    low, high = grade_bounds(grade, "ENB", 2.0)
    assert low < high
    coeffs = calibrate_mooney_coefficients()
    assert {"a0", "a1", "a2", "a3", "a4", "a5"}.issubset(coeffs)
    enb_fit = calibrate_enb_feed_relationship()
    assert math.isfinite(enb_fit["slope"])
    mooney = estimate_mooney(360000.0, 3.2, 55.0, 6.0)
    assert mooney > 0
    assert math.isfinite(estimate_tg(55.0, 39.0, 6.0))
    tm, risk = estimate_tm_and_crystallinity(70.0, 25.0)
    assert tm is not None and "risk" in risk
    fouling, level = fouling_risk_index(20.0, 360000.0, 3.2, 55.0, 373.15, mooney)
    assert fouling >= 0
    assert level in {"low", "medium", "high"}
    match = grade_match({"C2_wt": 55.0, "ENB_wt": 5.2, "Mooney": 80.0, "Mw": 360000.0, "PDI": 3.2}, "Vistalon_6602_like")
    assert 0 <= match["score"] <= 100
    assert generate_recommendations({"C2_wt": 55.0, "ENB_wt": 6.0, "Mooney": 80.0, "fouling_index": 0.5})


def test_plotting_remaining_figures_are_nonempty_and_labeled():
    flash = SimpleNamespace(split_table=pd.DataFrame({"component": ["C2", "solvent"], "vapor_kg_h": [1.0, 0.2], "liquid_kg_h": [0.1, 5.0]}))
    figures = [
        flash_split_chart(flash),
        sensitivity_line(pd.DataFrame({"value": [1, 2, 3], "Mooney": [60.0, 70.0, 80.0]}), "Mooney"),
        sensitivity_heatmap(pd.DataFrame({"T": [90, 90, 110, 110], "P": [0.7, 1.0, 0.7, 1.0], "ENB_wt": [5, 4.8, 6, 5.6]}), "T", "P", "ENB_wt"),
        optimization_convergence([{"iteration": 0, "objective": 3.0}, {"iteration": 1, "objective": 1.5}]),
        property_curve(pd.DataFrame({"T_C": [80, 100, 120], "mu_Pa_s": [0.03, 0.02, 0.015]}), "T_C", "mu_Pa_s", "黏度曲线", "黏度 Pa.s"),
    ]
    for fig in figures:
        assert validate_nonempty_figure(fig)[0].passed
    assert "kg/h" in figures[0].data[0].name
    assert figures[-1].layout.yaxis.title.text == "黏度 Pa.s"


def test_heat_balance_direct_functions_preserve_sign_and_units():
    q = calculate_reaction_heat({"ethylene": 10.0, "propylene": 5.0, "ENB": 1.0})
    assert q > 0
    assert thermal_risk_level(15.0) in {"low", "medium", "high"}
    lmtd = calculate_lmtd(100.0, 25.0, 35.0)
    assert lmtd > 0
    capacity, capacity_lmtd = heat_transfer_capacity_kW(300.0, 2.0, 100.0, 25.0, 35.0)
    assert capacity > 0
    assert capacity_lmtd > 0
    result = calculate_heat_balance(
        mol_consumed_h={"ethylene": 10.0, "propylene": 5.0, "ENB": 1.0},
        mass_holdup_kg=120.0,
        Cp_mix_kJ_kgK=2.2,
        config=HeatBalanceConfig(reactor_temperature_C=100.0),
    )
    assert result.Q_rxn_kW > 0
    assert math.isfinite(result.cooling_margin_kW)


def test_ui_theme_render_helpers_can_be_called(monkeypatch):
    calls: list[str] = []

    def fake_markdown(body, *args, **kwargs):
        calls.append(str(body))

    monkeypatch.setattr("streamlit.markdown", fake_markdown)
    install_safe_alerts()
    apply_theme("浅色")
    top_bar("case", "normal", "浅色")
    kpi_grid([("温度", "100 °C", "正常", "#22d3ee")])
    section_title("工程逻辑")
    assert calls
    assert any("Metallocene EPDM Digital Twin" in item for item in calls)
    assert any("epdm-kpi-grid" in item for item in calls)
