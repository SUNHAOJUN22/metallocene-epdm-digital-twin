"""Phase-equilibrium physical constraints and flash residual diagnostics."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd

from .eos import cubic_eos_details
from .flash import Flash, FlashResult, diagnose_flash_result
from .flowsheet import load_default_config, run_flowsheet
from .utils import c_to_k, mpa_to_pa


@dataclass(frozen=True)
class PhaseEquilibriumConstraint:
    """One physical constraint check for K-values, EOS roots or flash split."""

    check_id: str
    passed: bool
    severity: str
    value: float | str
    unit: str
    message: str
    fallback_reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def classify_z_roots(component: str, temperature_K: float, pressure_Pa: float, eos: str = "PR") -> dict[str, Any]:
    """Classify cubic-EOS roots and fugacity diagnostics for one component."""
    details = cubic_eos_details(component, temperature_K, pressure_Pa, eos)
    roots = sorted(float(value) for value in details.get("Z_roots", []) if float(value) > 0.0)
    return {
        "component": component,
        "eos": eos,
        "roots": roots,
        "liquid_root": roots[0] if roots else float(details.get("Z_liquid", 0.0)),
        "vapor_root": roots[-1] if roots else float(details.get("Z_vapor", 0.0)),
        "root_order_valid": bool(roots and roots[-1] >= roots[0]),
        "phi_v": float(details.get("phi_v", 0.0)),
        "phi_l": float(details.get("phi_l", 0.0)),
        "K": float(details.get("K", 0.0)),
        "fallback_reason": str(details.get("mode", "")),
    }


def k_value_ordering_dataframe(temperature_K: float = 373.15, pressure_Pa: float = 1.0e6) -> pd.DataFrame:
    """Return K-value ordering checks for light/heavy/polymer pseudo components."""
    names = ["hydrogen", "ethylene", "propylene", "ENB", "hexane", "polymer_EPDM"]
    rows = []
    for name in names:
        diag = classify_z_roots(name, temperature_K, pressure_Pa, "PR")
        rows.append({"component": name, "K": diag["K"], "phi_v": diag["phi_v"], "phi_l": diag["phi_l"], "root_order_valid": diag["root_order_valid"]})
    df = pd.DataFrame(rows)
    light_min = float(df[df["component"].isin(["hydrogen", "ethylene", "propylene"])]["K"].min())
    heavy_max = float(df[df["component"].isin(["ENB", "hexane", "polymer_EPDM"])]["K"].max())
    df["ordering_passed"] = light_min >= heavy_max or heavy_max < 1.0e-6
    return df


def flash_residuals_dataframe(result: FlashResult) -> pd.DataFrame:
    """Return RR, phase, polymer-vapor and total-mass residual rows for a flash result."""
    diag = diagnose_flash_result(result)
    vapor_mass = result.vapor.total_mass_flow()
    liquid_mass = result.liquid.total_mass_flow()
    table_feed = float(result.split_table["feed_kg_h"].sum()) if not result.split_table.empty else vapor_mass + liquid_mass
    polymer_mass = float(result.liquid.polymer_mass_kg_h)
    rows = [
        {"residual_id": "rachford_rice_residual", "value": float(diag.rr_residual), "unit": "-", "passed": abs(float(diag.rr_residual)) <= 1.0e-5, "severity": "ok"},
        {"residual_id": "flash_component_split", "value": abs(table_feed - (vapor_mass + liquid_mass - polymer_mass)), "unit": "kg/h", "passed": abs(table_feed - (vapor_mass + liquid_mass - polymer_mass)) <= 1.0e-6, "severity": "ok"},
        {"residual_id": "flash_polymer_vapor", "value": float(result.vapor.polymer_mass_kg_h), "unit": "kg/h", "passed": float(result.vapor.polymer_mass_kg_h) <= 1.0e-12, "severity": "critical" if result.vapor.polymer_mass_kg_h > 1.0e-12 else "ok"},
        {"residual_id": "flash_vapor_fraction_bounds", "value": float(result.vapor_fraction), "unit": "-", "passed": 0.0 <= float(result.vapor_fraction) <= 1.0, "severity": "ok" if 0.0 <= float(result.vapor_fraction) <= 1.0 else "error"},
    ]
    return pd.DataFrame(rows)


def phase_equilibrium_constraints_dataframe(result: Any | None = None) -> pd.DataFrame:
    """Return default phase-equilibrium physical constraint checks."""
    if result is None:
        result = run_flowsheet(load_default_config())
    checks: list[PhaseEquilibriumConstraint] = []
    root_diag = classify_z_roots("ethylene", c_to_k(100.0), mpa_to_pa(1.0), "PR")
    checks.append(PhaseEquilibriumConstraint("eos_root_order", bool(root_diag["root_order_valid"]), "error", float(root_diag["vapor_root"]) - float(root_diag["liquid_root"]), "-", "vapor root should be greater than or equal to liquid root", str(root_diag.get("fallback_reason", ""))))
    checks.append(PhaseEquilibriumConstraint("fugacity_positive", root_diag["phi_v"] > 0.0 and root_diag["phi_l"] > 0.0, "error", f"phi_v={root_diag['phi_v']}; phi_l={root_diag['phi_l']}", "-", "fugacity coefficients must be positive"))
    ordering = k_value_ordering_dataframe(c_to_k(100.0), mpa_to_pa(1.0))
    checks.append(PhaseEquilibriumConstraint("k_value_ordering", bool(ordering["ordering_passed"].all()), "warning", "light K values compared with heavy/polymer K values", "-", "light components should be more volatile than solvent/polymer in screening order"))
    inlet = result.streams["Quenched solution"]
    high_p = Flash("v5_4_high").calculate(inlet, c_to_k(100.0), mpa_to_pa(0.5))
    low_p = Flash("v5_4_low").calculate(inlet, c_to_k(100.0), mpa_to_pa(0.05))
    hot = Flash("v5_4_hot").calculate(inlet, c_to_k(140.0), mpa_to_pa(0.2))
    cool = Flash("v5_4_cool").calculate(inlet, c_to_k(80.0), mpa_to_pa(0.2))
    checks.append(PhaseEquilibriumConstraint("flash_pressure_monotonic", low_p.vapor_fraction >= high_p.vapor_fraction, "warning", low_p.vapor_fraction - high_p.vapor_fraction, "-", "lower pressure should not reduce vapor fraction"))
    light_hot = sum(hot.vapor.mass_flows.get(name, 0.0) for name in ["hydrogen", "ethylene", "propylene"])
    light_cool = sum(cool.vapor.mass_flows.get(name, 0.0) for name in ["hydrogen", "ethylene", "propylene"])
    checks.append(PhaseEquilibriumConstraint("flash_temperature_light_recovery", light_hot >= light_cool, "warning", light_hot - light_cool, "kg/h", "higher temperature should not lower light-component vapor recovery"))
    flash_rows = flash_residuals_dataframe(result.flash1)
    checks.append(PhaseEquilibriumConstraint("flash_residuals_pass", bool(flash_rows["passed"].all()), "error", float(flash_rows.loc[~flash_rows["passed"], "value"].sum()) if (~flash_rows["passed"]).any() else 0.0, "-", "RR/component/polymer vapor flash residuals should pass"))
    return pd.DataFrame([check.as_dict() for check in checks])

