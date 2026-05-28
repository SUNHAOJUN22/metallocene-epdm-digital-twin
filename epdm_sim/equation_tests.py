"""Equation-registry to code consistency checks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .flash import Flash
from .fluid_props import polymer_solution_viscosity, calculate_pipe_hydraulics
from .heat_balance import calculate_reaction_heat
from .kinetics import KineticParameters, arrhenius, pressure_factor_enb, estimate_molecular_weight
from .polymer_props import estimate_tg, grade_match
from .solubility import liquid_saturation_concentration_mol_L
from .thermo import ThermoEngine, solve_rachford_rice
from .streams import Stream


@dataclass(frozen=True)
class EquationCodeCheck:
    """One formula-to-code behavioral check."""

    equation_id: str
    function_under_test: str
    test_type: str
    expected_behavior: str
    passed: bool
    diagnostic: str
    severity: str = "error"

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def _check(equation_id: str, fn: str, test_type: str, behavior: str, passed: bool, diagnostic: str, severity: str = "error") -> EquationCodeCheck:
    return EquationCodeCheck(equation_id, fn, test_type, behavior, bool(passed), diagnostic, severity)


def run_equation_code_checks() -> list[EquationCodeCheck]:
    """Run lightweight trend checks for critical registered equations."""
    p = KineticParameters()
    checks: list[EquationCodeCheck] = []
    k_low = arrhenius(p.k_E_ref, p.Ea_E_J_mol, 330.0, p.T_ref_K)
    k_high = arrhenius(p.k_E_ref, p.Ea_E_J_mol, 390.0, p.T_ref_K)
    checks.append(_check("arrhenius_rate", "arrhenius", "monotonic", "T升高，k不下降", k_high >= k_low > 0, f"k_low={k_low:.4g}, k_high={k_high:.4g}"))
    pf_low = pressure_factor_enb(0.7, p)
    pf_high = pressure_factor_enb(2.0, p)
    checks.append(_check("enb_pressure_factor", "pressure_factor_enb", "monotonic", "P从0.7到2.0，factor不升", pf_high <= pf_low, f"pf_0.7={pf_low:.4g}, pf_2.0={pf_high:.4g}"))
    mw_low_h2 = estimate_molecular_weight(p.Mw0, 0.001, 55.0, 10.0, p)
    mw_high_h2 = estimate_molecular_weight(p.Mw0, 0.02, 55.0, 10.0, p)
    checks.append(_check("hydrogen_chain_transfer_mw", "estimate_molecular_weight", "monotonic", "H2升高，Mw下降", mw_high_h2 <= mw_low_h2, f"Mw_lowH2={mw_low_h2:.0f}, Mw_highH2={mw_high_h2:.0f}"))
    q1 = calculate_reaction_heat({"ethylene": 10.0}, {"ethylene": -95.0})
    q2 = calculate_reaction_heat({"ethylene": 20.0}, {"ethylene": -95.0})
    checks.append(_check("reaction_heat", "calculate_reaction_heat", "monotonic", "consumed mol增加，Q_rxn增加", q2 >= q1 > 0, f"Q1={q1:.3g}, Q2={q2:.3g}"))
    K = ThermoEngine("Simple Wilson K").k_values(["ethylene", "propylene", "hexane"], 373.15, 1.0e6)
    checks.append(_check("wilson_k", "wilson_k_values", "bounded", "K finite positive", all(np.isfinite(list(K.values()))) and min(K.values()) > 0, str(K)))
    V = solve_rachford_rice(np.array([0.2, 0.2, 0.6]), np.array([K["ethylene"], K["propylene"], K["hexane"]]))
    checks.append(_check("rachford_rice", "rachford_rice_vapor_fraction", "bounded", "V in [0,1]", 0.0 <= V <= 1.0 and np.isfinite(V), f"V={V:.4g}"))
    c_low = liquid_saturation_concentration_mol_L("ethylene", "hexane", 373.15, 0.5)
    c_high = liquid_saturation_concentration_mol_L("ethylene", "hexane", 373.15, 1.5)
    checks.append(_check("henry_cstar", "dissolved_concentration", "monotonic", "压力升高，Cstar升高", c_high >= c_low >= 0, f"C_low={c_low:.4g}, C_high={c_high:.4g}"))
    viscosity_stream = Stream.from_mass_flows("viscosity_check", 373.15, 1.0e6, {"hexane": 100.0, "ENB": 1.0})
    mu_solid_low = polymer_solution_viscosity(viscosity_stream, 373.15, 300000.0, solids_wt_override=5.0)
    mu_solid_high = polymer_solution_viscosity(viscosity_stream, 373.15, 300000.0, solids_wt_override=20.0)
    checks.append(_check("solution_viscosity_solids", "polymer_solution_viscosity", "monotonic", "solids升高，mu升高", mu_solid_high >= mu_solid_low > 0, f"mu_low={mu_solid_low:.4g}, mu_high={mu_solid_high:.4g}"))
    mu_temp_low = polymer_solution_viscosity(viscosity_stream, 393.15, 300000.0, solids_wt_override=10.0)
    mu_temp_high = polymer_solution_viscosity(viscosity_stream, 333.15, 300000.0, solids_wt_override=10.0)
    checks.append(_check("solution_viscosity_temperature", "polymer_solution_viscosity", "monotonic", "T升高，mu下降", mu_temp_low <= mu_temp_high, f"mu_393={mu_temp_low:.4g}, mu_333={mu_temp_high:.4g}"))
    dp_large = calculate_pipe_hydraulics(650.0, 0.01, 1.0, 10.0, 0.05).pressure_drop_kPa
    dp_small = calculate_pipe_hydraulics(650.0, 0.01, 1.0, 10.0, 0.025).pressure_drop_kPa
    checks.append(_check("darcy_weisbach_pressure_drop", "calculate_pipe_hydraulics", "monotonic", "pipe D下降，DeltaP上升", dp_small >= dp_large >= 0, f"dp_D05={dp_large:.4g}, dp_D025={dp_small:.4g}"))
    tg = estimate_tg(55.0, 38.0, 7.0)
    checks.append(_check("fox_tg", "estimate_tg", "finite", "Tg finite", np.isfinite(tg), f"Tg={tg:.3g}"))
    near = grade_match({"C2_wt": 55, "ENB_wt": 5.2, "Mooney": 80, "PDI": 3.4}, "Vistalon_6602_like")["score"]
    far = grade_match({"C2_wt": 75, "ENB_wt": 1.0, "Mooney": 20, "PDI": 5.0}, "Vistalon_6602_like")["score"]
    checks.append(_check("grade_match_score", "grade_match", "monotonic", "越接近目标，匹配score越高", near > far, f"near={near:.3g}, far={far:.3g}"))
    return checks


def equation_code_checks_dataframe(checks: list[EquationCodeCheck] | None = None) -> pd.DataFrame:
    """Return equation-code checks as a DataFrame."""
    return pd.DataFrame([check.as_dict() for check in (checks or run_equation_code_checks())])
