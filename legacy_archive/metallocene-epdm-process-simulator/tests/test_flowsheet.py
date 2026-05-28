import math

from epdm_sim.flowsheet import build_process_graph, load_default_config, run_flowsheet
from epdm_sim.optimizer import optimize_for_grade
from epdm_sim.report import export_excel, export_word_report


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
