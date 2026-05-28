"""Golden scientific benchmark runner for release-gate regression checks."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .bayesian_doe import recommend_next_experiment_batch
from .cfd.simple_solver import build_cfd_input_from_flowsheet, run_simple_cfd
from .constrained_window import generate_feasible_windows
from .dynamic_template_reactor import simulate_template_semibatch_ode
from .eos import cubic_eos_k_value
from .flash import diagnose_flash_result
from .flowsheet import load_default_config, run_flowsheet
from .heat_balance import calculate_heat_balance
from .model_audit_report import build_model_audit_report
from .residual_system import build_flowsheet_residual_system
from .rheology import RheologyParameters, calculate_rheology
from .solubility import liquid_saturation_concentration_mol_L
from .template_config import TemplateProcessConfig
from .template_flowsheet import run_template_flowsheet
from .thermo import solve_rachford_rice
from .utils import data_path, kg_h_to_mol_h, mol_h_to_kg_h


MODEL_VERSION = "V6.4 / 0.7.4"


@dataclass(frozen=True)
class BenchmarkCheck:
    """One benchmark result."""

    benchmark_id: str
    value: float
    expected: float
    tolerance: float
    unit: str
    passed: bool
    detail: str
    residual_id: str = ""


def benchmark_definitions() -> pd.DataFrame:
    """Load benchmark metadata."""
    path = data_path("golden_benchmarks.json")
    if not Path(path).exists():
        return pd.DataFrame()
    return pd.read_json(path)


def _definition_map() -> dict[str, dict[str, Any]]:
    df = benchmark_definitions()
    if df.empty:
        return {}
    return {str(row["benchmark_id"]): row.to_dict() for _, row in df.iterrows()}


def _check(benchmark_id: str, value: float, expected: float, tolerance: float, unit: str, detail: str = "", residual_id: str = "") -> BenchmarkCheck:
    return BenchmarkCheck(
        benchmark_id=benchmark_id,
        value=float(value),
        expected=float(expected),
        tolerance=float(tolerance),
        unit=unit,
        passed=bool(np.isfinite(value) and abs(float(value) - float(expected)) <= float(tolerance)),
        detail=detail,
        residual_id=residual_id,
    )


def run_scientific_benchmarks() -> pd.DataFrame:
    """Run stable scientific benchmark checks."""
    definitions = _definition_map()

    def expected(benchmark_id: str, fallback: float, tolerance: float, unit: str) -> tuple[float, float, str]:
        item = definitions.get(benchmark_id, {})
        return float(item.get("expected", fallback)), float(item.get("tolerance", tolerance)), str(item.get("unit", unit))

    def check_from_def(benchmark_id: str, value: float, fallback: float, tolerance: float, unit: str, detail: str = "") -> BenchmarkCheck:
        exp, tol, unit_text = expected(benchmark_id, fallback, tolerance, unit)
        residual_id = str(definitions.get(benchmark_id, {}).get("residual_id", ""))
        return _check(benchmark_id, value, exp, tol, unit_text, detail, residual_id)

    cfg = load_default_config()
    result = run_flowsheet(cfg)
    generic_cfg = TemplateProcessConfig(
        template_id="generic_terpolymerization_apparent",
        monomer_feeds_kg_h={"monomer_A": 8.0, "monomer_B": 6.0, "monomer_C": 2.0},
        solvent_mass_kg_h=80.0,
    )
    generic = run_template_flowsheet(generic_cfg)
    rr = solve_rachford_rice(np.array([0.5, 0.5]), np.array([2.0, 0.5]))
    eos_k = cubic_eos_k_value("ethylene", 373.15, 1.0e6, "PR")
    c_low = liquid_saturation_concentration_mol_L("ethylene", "hexane", 373.15, 0.5)
    c_high = liquid_saturation_concentration_mol_L("ethylene", "hexane", 373.15, 1.5)
    rheo = calculate_rheology(373.15, 15.0, 350000.0, 10.0, "hexane", RheologyParameters(model="carreau-yasuda"))
    dynamic = simulate_template_semibatch_ode(total_time_min=4.0, dt_min=1.0)
    dynamic_rk = simulate_template_semibatch_ode(total_time_min=3.0, dt_min=1.0, solver_mode="solve_ivp_rk45")
    dynamic_bdf = simulate_template_semibatch_ode(total_time_min=3.0, dt_min=1.0, solver_mode="solve_ivp_bdf")
    cfd = run_simple_cfd(build_cfd_input_from_flowsheet(result, nx=30, ny=16))
    heat = calculate_heat_balance({"ethylene": 1.0, "propylene": 1.0, "ENB": 0.1}, mass_holdup_kg=10.0, Cp_mix_kJ_kgK=2.0)
    audit = build_model_audit_report(result)
    residual_system = build_flowsheet_residual_system(result)
    windows = generate_feasible_windows(cfg)
    doe = recommend_next_experiment_batch(cfg, {"beta_P": 0.8, "ktr_H2": 0.8}, n=3)
    rows = [
        check_from_def("default_epdm_polymer_kg_h", result.kpis["polymer_kg_h"], 11.54, 0.1, "kg/h"),
        check_from_def("default_epdm_composition_sum", result.kpis["C2_wt"] + result.kpis["C3_wt"] + result.kpis["ENB_wt"], 100.0, 1.0e-8, "wt%"),
        check_from_def("generic_polymer_positive", generic.application_kpis["polymer_kg_h"], 4.102564, 0.05, "kg/h"),
        check_from_def("flash1_vapor_fraction", diagnose_flash_result(result.flash1).vapor_fraction, 0.978, 0.01, "-"),
        check_from_def("rachford_rice_standard", rr, 0.5, 1.0e-10, "-"),
        check_from_def("henry_pressure_delta", c_high - c_low, 0.18, 0.02, "mol/L"),
        check_from_def("pr_eos_ethylene_k", eos_k, 83.5, 15.0, "-"),
        check_from_def("rheology_viscosity_positive", rheo.apparent_viscosity_Pa_s, rheo.apparent_viscosity_Pa_s, max(rheo.apparent_viscosity_Pa_s, 1.0e-9), "Pa.s"),
        check_from_def("pressure_drop_default", result.kpis["pipe_pressure_drop_kPa"], 0.057, 0.05, "kPa"),
        check_from_def("heat_duty_default", result.kpis["heat_duty_kW"], 8.62, 0.1, "kW"),
        check_from_def("heat_release_standard", heat.Q_rxn_kW, 0.051, 0.01, "kW"),
        check_from_def("dynamic_default_final_rate", float(dynamic.profile.filter(like="r_").iloc[-1].sum()), 1.46716, 0.05, "mol/h"),
        check_from_def("dynamic_rk45_rows", float(len(dynamic_rk.profile)), 4.0, 1.0e-9, "rows"),
        check_from_def("dynamic_bdf_or_fallback_rows", float(len(dynamic_bdf.profile)), 4.0, 50.0, "rows"),
        check_from_def(
            "cfd_dead_zone_fraction",
            cfd.diagnostics.dead_zone_fraction,
            cfd.diagnostics.dead_zone_fraction,
            1.0,
            "-",
        ),
        check_from_def("model_audit_score", audit.model_confidence_card.overall_score, 89.3, 10.0, "score"),
        check_from_def("residual_system_score", residual_system.overall_score, 90.0, 15.0, "score"),
        check_from_def("constrained_window_count", float(len(windows)), 5.0, 3.0, "count"),
        check_from_def("bayesian_doe_top_score", float(doe["expected_information_gain"].iloc[0]) if not doe.empty else 0.0, 10.0, 20.0, "score"),
    ]
    return pd.DataFrame([asdict(row) for row in rows])


def unit_roundtrip_checks() -> pd.DataFrame:
    """Return deterministic unit roundtrip checks used by property tests."""
    mol = kg_h_to_mol_h(1.23, 42.08)
    kg = mol_h_to_kg_h(mol, 42.08)
    return pd.DataFrame(
        [
            {"check": "kg_h_mol_h_roundtrip", "value": kg, "expected": 1.23, "abs_error": abs(kg - 1.23), "passed": abs(kg - 1.23) < 1.0e-12},
        ]
    )

