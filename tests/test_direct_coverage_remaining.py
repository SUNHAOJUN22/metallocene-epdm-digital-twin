from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from epdm_sim.cfd.grid_convergence import CFDGridConvergenceResult
from epdm_sim.cfd.simple_solver import SimpleCFDResult
from epdm_sim.doe_optimal import DOEOptimalResult
from epdm_sim.dynamic_stability import DynamicStabilityResult
from epdm_sim.dynamic_template_reactor import DynamicTemplateResult
from epdm_sim.engineering_checks import EngineeringCheckResult
from epdm_sim.engineering_rules import EngineeringRule, EngineeringRuleResult
from epdm_sim.equipment_3d import EquipmentDescriptor
from epdm_sim.experiment_data import load_experiment_file
from epdm_sim.feed_adapter import FeedValidationResult
from epdm_sim.flash import Flash, FlashDiagnostic, FlashResult
from epdm_sim.heat_balance import HeatBalanceResult
from epdm_sim.io_schema import ModelInputSpec, ModelIOSchema, ModelOutputSpec
from epdm_sim.kinetics import KineticParameters, RateResult
from epdm_sim.model_audit_report import ModelAuditReport
from epdm_sim.model_confidence import ModelConfidenceCard
from epdm_sim.model_registry import ModelModule
from epdm_sim.ode_scaling import BDFReadiness
from epdm_sim.optimizer import OptimizationResult
from epdm_sim.pareto import ParetoResult
from epdm_sim.plot_validation import PlotValidationResult, validate_axis_labels, validate_colorbar_labels
from epdm_sim.property_calibration import PropertyCalibrationResult
from epdm_sim.property_models import PolymerPropertyResult
from epdm_sim.reaction_templates import ReactionTemplate, get_reaction_template
from epdm_sim.recycle_solver import RecycleSolverResult
from epdm_sim.report_consistency import ReportConsistencyResult
from epdm_sim.safety import SafetyResult
from epdm_sim.scientific_benchmarks import BenchmarkCheck
from epdm_sim.services.simulation_service import TimedResult
from epdm_sim.solubility import SolubilityRecord
from epdm_sim.state import ResultsStore
from epdm_sim.state_vector import build_state_layout_from_template
from epdm_sim.streams import Stream
from epdm_sim.surrogate import SurrogateModel
from epdm_sim.template_config import process_config_to_template_config
from epdm_sim.template_flowsheet import TemplateFlowsheetResult
from epdm_sim.template_ode_rhs import TemplateODERHSContext
from epdm_sim.thermo import FlashSplit
from epdm_sim.thermo_calibration import ThermoCalibrationResult
from epdm_sim.thermo_consistency import ThermoConsistencyResult
from epdm_sim.ui_audit import UIAuditResult, audit_file
from epdm_sim.ui_workflow import UIAction
from epdm_sim.uncertainty import UncertaintyResult
from epdm_sim.unitops import FlashUnit, UnitOperation
from epdm_sim.validation_campaign import ValidationCampaignResult
from epdm_sim.validity_envelope import ValidityEnvelopeResult
from epdm_sim.workflow_wizard import WorkflowStep
from epdm_sim.flowsheet import load_default_config, run_flowsheet


def test_remaining_result_dataclasses_are_finite_and_bounded():
    empty = pd.DataFrame()
    assert CFDGridConvergenceResult("template", pd.DataFrame({"metric": ["max_T"], "value": [1.0]}), ["ethylene"], 95.0, []).convergence_score <= 100.0
    assert SimpleCFDResult("simple", None, None, None, [], None).mode == "simple"
    assert DOEOptimalResult(pd.DataFrame({"experiment_id": ["x"]}), pd.DataFrame()).recommendations.shape[0] == 1
    assert DynamicStabilityResult("nonnegative", True, "ok", "finite", {}).passed
    assert EngineeringCheckResult(True, "ok", "passed", "reactor", "").passed
    assert EngineeringRuleResult("rule", True, {"x": 1.0}, "increases", "ok", "passed", "").passed
    assert FlashDiagnostic(0.2, True, 0.0, "none", {"polymer_pseudo": "nonvolatile"}, []).phase_split_valid
    assert BDFReadiness(True, False, "scaled", 1.0, 10.0).ready
    assert ReportConsistencyResult("version", True, "ok", "matched").passed
    assert ThermoConsistencyResult("K_positive", True, "ok", "finite", {}).passed
    assert ValidityEnvelopeResult("m", "T", 50.0, "0-100", "inside", "ok", "inside").status == "inside"
    assert ValidationCampaignResult(88.0, empty, empty, empty).validation_score == 88.0
    assert BenchmarkCheck("b", 1.0, 1.0, 0.01, "kg/h", True, "ok").passed
    assert TimedResult("result", "hash", 0.01, False).elapsed_s >= 0.0
    assert ResultsStore().metadata == {}
    assert WorkflowStep("s1", "Start", ["config"], "run_fast_flowsheet", 0.1).target_action == "run_fast_flowsheet"


def test_io_schema_plot_validation_and_ui_audit_helpers(tmp_path):
    schema = ModelIOSchema(
        "test_model",
        inputs=[ModelInputSpec("temperature", "K", min_value=273.15, max_value=500.0)],
        outputs=[ModelOutputSpec("conversion", "%", physical_bounds=(0.0, 100.0))],
    )
    assert schema.inputs[0].unit == "K"

    fig = go.Figure(data=[go.Scatter(x=[0, 1], y=[1, 2], name="conversion %")])
    fig.update_layout(xaxis_title="time min", yaxis_title="conversion %")
    axis = validate_axis_labels(fig, "conversion")
    color = validate_colorbar_labels(fig, "conversion")
    assert all(isinstance(row, PlotValidationResult) for row in axis + color)
    assert all(row.passed for row in axis + color)

    path = tmp_path / "page.py"
    path.write_text("import streamlit as st\nif st.button('Run', key='run_once'):\n    st.write('ok')\n", encoding="utf-8")
    issues = audit_file(path)
    assert all(isinstance(item, UIAuditResult) for item in issues)


def test_flash_unit_operation_and_flash_result_close_mass():
    feed = Stream.from_mass_flows("feed", 323.15, 1.0e6, {"hexane": 1.0, "ethylene": 0.05})
    unit = FlashUnit(name="flash", inlet_streams=[feed], temperature_C=70.0, pressure_MPa=0.1)
    assert issubclass(FlashUnit, UnitOperation)
    result = unit.calculate()
    assert isinstance(result, FlashResult)
    assert 0.0 <= result.vapor_fraction <= 1.0
    assert abs(result.vapor.total_mass_flow() + result.liquid.total_mass_flow() - feed.total_mass_flow()) < 1.0e-9
    direct = Flash("direct").calculate(feed, 343.15, 1.0e5)
    assert direct.vapor.polymer_mass_kg_h == 0.0


def test_template_flow_dynamic_and_model_audit_structures():
    cfg = load_default_config()
    result = run_flowsheet(cfg)
    template_cfg = process_config_to_template_config(cfg)
    template_result = TemplateFlowsheetResult(
        template_cfg,
        template_cfg.template_id,
        result.streams,
        {},
        result.reactor,
        {},
        result.heat_balance,
        result.fluid_properties,
        result.pipe_hydraulics,
        None,
        [],
        result.kpis,
        legacy_flowsheet=result,
    )
    assert template_result.template_id == template_cfg.template_id

    layout = build_state_layout_from_template(template_cfg.template_id)
    dynamic = DynamicTemplateResult(template_cfg.template_id, layout, pd.DataFrame({"time_min": [0.0], "polymer_mass_kg": [0.0]}), {"solver": "explicit"})
    assert dynamic.profile["polymer_mass_kg"].ge(0.0).all()

    card = ModelConfidenceCard(90.0, 90.0, 90.0, 90.0, 90.0, 80.0, 100.0)
    audit = ModelAuditReport(card, *(pd.DataFrame() for _ in range(10)))
    assert audit.model_confidence_card.overall_score == 90.0


def test_scientific_and_calibration_payload_classes(tmp_path):
    rule = EngineeringRule("r1", "desc", "module", "x", "y", "increases", "always", [1.0, 2.0], 0.0, "rationale", "warning", "fix")
    assert rule.expected_trend == "increases"
    equipment = EquipmentDescriptor("R1", "反应釜", "reaction", 0.0, 0.0, 0.0, key_metric="T=70 C")
    assert equipment.equipment_id == "R1"
    feed_validation = FeedValidationResult(True, "ok", "valid")
    assert feed_validation.passed
    heat = HeatBalanceResult(1, 1, 0, 0, 0, 0, 0, 1, 1, 10, 2, 5, "low", 2, 1, 10, "ok", {"ethylene": -95})
    assert heat.cooling_margin_kW > 0.0
    rate = RateResult(1, 1, 1, 2, 2, 2, 0.1, 1, 1, 1)
    assert min(rate.r_E_mol_L_h, rate.r_P_mol_L_h, rate.r_ENB_mol_L_h) >= 0.0
    opt = OptimizationResult("grade", True, True, 1.0, -1.0, cfg := load_default_config(), {"Mw": 100000})
    assert opt.success and opt.feasible
    assert ParetoResult(pd.DataFrame({"x": [1]}), pd.DataFrame({"x": [1]}), pd.DataFrame()).frontier.shape[0] == 1
    prop_cal = PropertyCalibrationResult("viscosity", {"A": 1.0}, {"A": (0.5, 1.5)}, pd.DataFrame({"r": [0.0]}), {"T": (300.0, 400.0)})
    thermo_cal = ThermoCalibrationResult("henry", {"H": 1.0}, {"H": (0.5, 1.5)}, pd.DataFrame({"r": [0.0]}), {"P": (0.1, 2.0)})
    assert prop_cal.fitted_params["A"] == 1.0 and thermo_cal.fitted_params["H"] == 1.0
    poly = PolymerPropertyResult("template", "generic", {"A": 100.0}, 100000.0, 50000.0, 2.0, 50.0, -50.0, None, "low", 0.2, "low")
    assert poly.PDI >= 1.0 and poly.Mooney > 0.0
    template = get_reaction_template("EPDM_EPM_metallocene_solution")
    explicit = ReactionTemplate(**template.__dict__)
    assert "ethylene" in explicit.monomers
    recycle = RecycleSolverResult({"hexane": 1.0}, {"hexane": 0.1}, {"hexane": 0.01}, 2, 0.0, 99.0, 98.0)
    assert recycle.closure_error == 0.0
    safety = SafetyResult(1.0, 5.0, 10.0, 85.0, "adequate", "low", ["monitor"])
    assert safety.runaway_risk_level == "low"
    sol = SolubilityRecord("ethylene", "hexane", 0.2, -10000.0)
    assert sol.solubility_ref_mol_L_MPa > 0.0
    surrogate = SurrogateModel("Mw", ["H2"], "linear", [-1.0], 100000.0, "hash", {"H2": (0.0, 10.0)}, {"r2": 1.0})
    assert surrogate.coefficients[0] < 0.0
    split = FlashSplit(0.2, {"hexane": 1.0}, {"hexane": 1.0}, {"hexane": 0.1}, "Wilson")
    assert 0.0 <= split.vapor_fraction <= 1.0
    uncertainty = UncertaintyResult(pd.DataFrame({"x": [1]}), pd.DataFrame({"metric": ["Mw"]}), pd.DataFrame(), {"p": 0.0}, {})
    assert uncertainty.risk_probabilities["p"] == 0.0

    csv_path = tmp_path / "exp.csv"
    csv_path.write_text("run_id,temperature_C,pressure_MPa\nr1,70,1.0\n", encoding="utf-8")
    loaded = load_experiment_file(csv_path)
    assert loaded.loc[0, "run_id"] == "r1"


def test_registry_actions_and_rhs_context():
    module = ModelModule("m", "M", "cat", "local", "impl", "auto_cached", ["eq"], ["x"], ["y"], required_units={"x": "kg/h"})
    assert module.required_units["x"] == "kg/h"
    action = UIAction("a", "Run", "page", "button_manual", "task", reads=["config"], writes=["result"])
    assert action.trigger_type == "button_manual"

    template = get_reaction_template("EPDM_EPM_metallocene_solution")
    layout = build_state_layout_from_template(template.template_id)
    ctx = TemplateODERHSContext(
        template,
        layout,
        KineticParameters(),
        {"ethylene": 1.0},
        {"hydrogen": 0.0},
        1.0,
        1.0e6,
        300.0,
        10.0,
    )
    assert ctx.reactor_volume_L > 0.0
