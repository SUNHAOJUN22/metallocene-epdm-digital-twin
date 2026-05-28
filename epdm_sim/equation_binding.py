"""Bind equation registry records to implementation functions and trend checks."""

from __future__ import annotations

import importlib
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd

from .equation_registry import load_equation_registry


IMPLEMENTATION_MAP = {
    "arrhenius_rate_constant": "epdm_sim.kinetics.arrhenius",
    "activation_factor": "epdm_sim.kinetics.activation_factor",
    "enb_pressure_factor": "epdm_sim.kinetics.pressure_factor_enb",
    "hydrogen_chain_transfer_mw": "epdm_sim.kinetics.estimate_molecular_weight",
    "reaction_heat_release": "epdm_sim.heat_balance.calculate_reaction_heat",
    "adiabatic_temperature_rise": "epdm_sim.heat_balance.calculate_heat_balance",
    "wilson_k_value": "epdm_sim.thermo.wilson_k_value",
    "rachford_rice": "epdm_sim.thermo.solve_rachford_rice",
    "eos_fugacity_k": "epdm_sim.eos.cubic_eos_k_value",
    "henry_liquid_saturation": "epdm_sim.solubility.liquid_saturation_concentration_mol_L",
    "solution_viscosity": "epdm_sim.rheology.zero_shear_solution_viscosity",
    "power_law_viscosity": "epdm_sim.rheology.apparent_viscosity_from_zero_shear",
    "carreau_yasuda_viscosity": "epdm_sim.rheology.apparent_viscosity_from_zero_shear",
    "darcy_weisbach_pressure_drop": "epdm_sim.fluid_props.calculate_pipe_hydraulics",
    "fox_tg": "epdm_sim.polymer_props.estimate_tg",
    "grade_match_score": "epdm_sim.polymer_props.grade_match",
    "template_liquid_monomer_balance": "epdm_sim.template_ode_rhs.template_ode_rhs",
}

BENCHMARK_MAP = {
    "arrhenius_rate_constant": "arrhenius_rate_ratio",
    "reaction_heat_release": "heat_release_standard",
    "henry_liquid_saturation": "henry_pressure_delta",
    "eos_fugacity_k": "pr_eos_ethylene_k",
    "rachford_rice": "rachford_rice_standard",
    "carreau_yasuda_viscosity": "rheology_viscosity_positive",
    "darcy_weisbach_pressure_drop": "pressure_drop_default",
    "grade_match_score": "model_audit_score",
}

RESIDUAL_MAP = {
    "reaction_heat_release": "heat_release_proxy",
    "adiabatic_temperature_rise": "heat_release_proxy",
    "rachford_rice": "flash_phase_mass",
    "eos_fugacity_k": "flash_phase_mass",
    "template_liquid_monomer_balance": "dynamic_accumulation",
    "template_energy_balance": "dynamic_energy_balance",
    "darcy_weisbach_pressure_drop": "transport_pressure_drop",
    "carreau_yasuda_viscosity": "transport_viscosity",
}


@dataclass(frozen=True)
class EquationBinding:
    """One registry-to-code binding."""

    equation_id: str
    implementation_function: str
    input_units: dict[str, str]
    output_unit: str
    dimensional_signature: str
    expected_trends: str
    benchmark_id: str
    residual_id: str
    fallback_policy: str
    importable: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def import_implementation(dotted_path: str) -> Any:
    """Import an implementation function from a dotted path."""
    module_name, function_name = dotted_path.rsplit(".", 1)
    return getattr(importlib.import_module(module_name), function_name)


def load_equation_bindings() -> dict[str, EquationBinding]:
    """Build bindings from equation registry plus V5.3 implementation metadata."""
    bindings: dict[str, EquationBinding] = {}
    for equation_id, spec in load_equation_registry().items():
        impl = IMPLEMENTATION_MAP.get(equation_id, "")
        importable = False
        if impl:
            try:
                import_implementation(impl)
                importable = True
            except Exception:
                importable = False
        bindings[equation_id] = EquationBinding(
            equation_id=equation_id,
            implementation_function=impl,
            input_units=dict(spec.variable_units),
            output_unit=spec.output_unit,
            dimensional_signature=spec.dimensional_check,
            expected_trends=_expected_trend(equation_id),
            benchmark_id=BENCHMARK_MAP.get(equation_id, equation_id),
            residual_id=RESIDUAL_MAP.get(equation_id, equation_id),
            fallback_policy=spec.fallback,
            importable=importable,
        )
    return bindings


def _expected_trend(equation_id: str) -> str:
    trends = {
        "arrhenius_rate_constant": "temperature increases -> k nondecreasing",
        "enb_pressure_factor": "pressure above 0.7 MPa increases -> factor nonincreasing",
        "hydrogen_chain_transfer_mw": "hydrogen increases -> Mw nonincreasing",
        "reaction_heat_release": "consumed mol increases -> heat release increases",
        "henry_liquid_saturation": "pressure increases -> Cstar increases",
        "solution_viscosity": "solids and Mw increase -> viscosity increases; T increases -> viscosity decreases",
        "darcy_weisbach_pressure_drop": "diameter decreases or flow increases -> pressure drop increases",
    }
    return trends.get(equation_id, "finite bounded output under validity range")


def equation_binding_dataframe() -> pd.DataFrame:
    """Return equation bindings as a report table."""
    return pd.DataFrame([binding.as_dict() for binding in load_equation_bindings().values()])


def validate_equation_bindings(critical_equations: list[str] | None = None) -> list[str]:
    """Return binding errors for critical equations."""
    critical_equations = critical_equations or list(IMPLEMENTATION_MAP)
    bindings = load_equation_bindings()
    errors: list[str] = []
    for equation_id in critical_equations:
        binding = bindings.get(equation_id)
        if binding is None:
            errors.append(f"{equation_id} missing from registry")
            continue
        if not binding.implementation_function:
            errors.append(f"{equation_id} missing implementation_function")
        if not binding.importable:
            errors.append(f"{equation_id} implementation is not importable")
        if not binding.output_unit:
            errors.append(f"{equation_id} missing output_unit")
        if not binding.dimensional_signature:
            errors.append(f"{equation_id} missing dimensional_signature")
        if not binding.residual_id:
            errors.append(f"{equation_id} missing residual_id")
    return errors


def run_equation_binding_checks() -> pd.DataFrame:
    """Run importability and metadata checks for release gates."""
    bindings = load_equation_bindings()
    rows = []
    for binding in bindings.values():
        rows.append(
            {
                "equation_id": binding.equation_id,
                "implementation_function": binding.implementation_function,
                "importable": binding.importable,
                "has_units": bool(binding.input_units and binding.output_unit),
                "has_dimensional_signature": bool(binding.dimensional_signature),
                "has_benchmark": bool(binding.benchmark_id),
                "has_residual_id": bool(binding.residual_id),
                "passed": bool(binding.importable or binding.equation_id not in IMPLEMENTATION_MAP),
            }
        )
    return pd.DataFrame(rows)


def trend_smoke_results() -> pd.DataFrame:
    """Return lightweight finite trend checks for critical equations."""
    from .heat_balance import calculate_reaction_heat
    from .kinetics import arrhenius, pressure_factor_enb
    from .solubility import liquid_saturation_concentration_mol_L
    from .thermo import solve_rachford_rice

    rows = [
        {"check": "arrhenius_T", "passed": arrhenius(1.0, 40000.0, 390.0) >= arrhenius(1.0, 40000.0, 350.0)},
        {"check": "enb_pressure", "passed": pressure_factor_enb(2.0) <= pressure_factor_enb(0.7)},
        {"check": "reaction_heat", "passed": calculate_reaction_heat({"ethylene": 2.0}) >= calculate_reaction_heat({"ethylene": 1.0})},
        {"check": "henry_pressure", "passed": liquid_saturation_concentration_mol_L("ethylene", "hexane", 373.15, 2.0) > liquid_saturation_concentration_mol_L("ethylene", "hexane", 373.15, 1.0)},
        {"check": "rachford_bounded", "passed": 0.0 <= solve_rachford_rice(np.array([0.5, 0.5]), np.array([2.0, 0.5])) <= 1.0},
    ]
    return pd.DataFrame(rows)
