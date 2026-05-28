import math

from epdm_sim.flowsheet import build_process_graph, load_default_config, run_flowsheet
from epdm_sim.optimizer import optimize_for_grade
from epdm_sim.report import export_excel, export_word_report
from epdm_sim.calibration import calibrate_from_internal_data, recommend_doe
from epdm_sim.scaleup import compare_scaleup


def test_flowsheet_mass_balance_and_product_composition():
    result = run_flowsheet(load_default_config())
    assert abs(result.kpis["mass_balance_error_pct"]) < 0.5
    total = result.kpis["C2_wt"] + result.kpis["C3_wt"] + result.kpis["ENB_wt"]
    assert abs(total - 100.0) < 1.0e-6
    assert result.kpis["polymer_kg_h"] >= 0.0
    assert result.kpis["heat_duty_kW"] > 0.0
    assert result.kpis["dynamic_viscosity_Pa_s"] > 0.0


def test_optimization_returns_feasible_result():
    cfg = load_default_config()
    opt = optimize_for_grade(cfg, "A", maxiter=1, enb_residue_threshold_ppm=1.0e9)
    assert math.isfinite(opt.objective)
    assert opt.feasible
    assert opt.config.temperature_C >= 80.0
    assert opt.score >= 0.0
    assert opt.kpis["polymer_kg_h"] >= 0.0


def test_process_graph_contains_recycles():
    graph = build_process_graph()
    assert graph.has_edge("Flash-1", "Gas recycle")
    assert graph.has_edge("Solvent/ENB recycle", "Mixer")


def test_reports_include_heat_and_fluid_tables():
    result = run_flowsheet(load_default_config())
    assert len(export_excel(result)) > 1000
    assert len(export_word_report(result)) > 1000


def test_reports_accept_calibration_doe_and_scaleup():
    cfg = load_default_config()
    result = run_flowsheet(cfg)
    calibration = calibrate_from_internal_data()
    doe = recommend_doe("ENB wt%", cfg, n=4)
    scaleup = compare_scaleup(result.kpis["liquid_density_kg_m3"], result.kpis["dynamic_viscosity_Pa_s"])
    assert len(export_excel(result, calibration=calibration, doe_df=doe, scaleup_df=scaleup)) > 1000
    assert len(export_word_report(result, calibration=calibration, doe_df=doe, scaleup_df=scaleup)) > 1000
