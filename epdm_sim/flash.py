"""Flash unit operation using Rachford-Rice and Wilson K values."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .components import load_components
from .dimensioned import ensure_pressure_Pa, ensure_temperature_K
from .streams import Stream
from .thermo import ThermoEngine
from .utils import TINY, mol_h_to_kg_h, positive, safe_divide


@dataclass
class FlashResult:
    """Flash split result."""

    vapor: Stream
    liquid: Stream
    vapor_fraction: float
    split_table: pd.DataFrame
    k_values: dict[str, float]
    mode: str
    duty_kJ_h: float


@dataclass
class FlashDiagnostic:
    """Phase-split diagnostic for flash robustness and chemical logic."""

    vapor_fraction: float
    phase_split_valid: bool
    rr_residual: float
    fallback_used: str
    component_distribution_flags: dict[str, str]
    warnings: list[str]

    def as_dataframe(self) -> pd.DataFrame:
        """Return diagnostic rows."""
        rows = [
            {"item": "vapor_fraction", "value": self.vapor_fraction, "status": "ok" if 0.0 <= self.vapor_fraction <= 1.0 else "error"},
            {"item": "phase_split_valid", "value": self.phase_split_valid, "status": "ok" if self.phase_split_valid else "error"},
            {"item": "rr_residual", "value": self.rr_residual, "status": "ok" if abs(self.rr_residual) < 1.0e-5 else "warning"},
            {"item": "fallback_used", "value": self.fallback_used, "status": "info"},
        ]
        rows.extend({"item": component, "value": flag, "status": "info"} for component, flag in self.component_distribution_flags.items())
        rows.extend({"item": "warning", "value": warning, "status": "warning"} for warning in self.warnings)
        return pd.DataFrame(rows)


class Flash:
    """Isothermal flash unit operation."""

    def __init__(self, name: str, thermo_mode: str = "Simple Wilson K"):
        self.name = name
        self.thermo = ThermoEngine(thermo_mode)

    def calculate(self, inlet: Stream, temperature_K: float, pressure_Pa: float) -> FlashResult:
        """Perform flash split for molecular components; polymer remains liquid."""
        temperature_K = ensure_temperature_K(temperature_K, default_unit="K")
        pressure_Pa = ensure_pressure_Pa(pressure_Pa, default_unit="Pa")
        components = load_components()
        molecular_moles = {
            name: positive(flow)
            for name, flow in inlet.molar_flows.items()
            if name in components and components[name].type != "polymer"
        }
        total_moles = sum(molecular_moles.values())
        split = self.thermo.flash(molecular_moles, temperature_K, pressure_Pa)
        vapor_moles: dict[str, float] = {}
        liquid_moles: dict[str, float] = {}
        if total_moles <= TINY:
            vapor_fraction = 0.0
        else:
            vapor_fraction = split.vapor_fraction
        vapor_total = vapor_fraction * total_moles
        liquid_total = (1.0 - vapor_fraction) * total_moles
        for name in molecular_moles:
            vapor_moles[name] = vapor_total * split.y.get(name, 0.0)
            liquid_moles[name] = liquid_total * split.x.get(name, 0.0)
        vapor = Stream(
            name=f"{self.name} vapor",
            temperature_K=temperature_K,
            pressure_Pa=pressure_Pa,
            molar_flows=vapor_moles,
            phase="vapor",
        )
        liquid = Stream(
            name=f"{self.name} liquid",
            temperature_K=temperature_K,
            pressure_Pa=pressure_Pa,
            molar_flows=liquid_moles,
            phase="liquid",
            polymer_mass_kg_h=inlet.polymer_mass_kg_h,
            segment_masses_kg_h=dict(inlet.segment_masses_kg_h),
        )
        vapor.sync_mass_from_moles(components)
        liquid.sync_mass_from_moles(components)
        liquid.polymer_mass_kg_h = inlet.polymer_mass_kg_h
        liquid.segment_masses_kg_h = dict(inlet.segment_masses_kg_h)
        liquid.update_solids()
        rows = []
        vaporized_mass = 0.0
        for name in molecular_moles:
            feed_mass = mol_h_to_kg_h(molecular_moles[name], components[name].MW)
            vapor_mass = vapor.mass_flows.get(name, 0.0)
            liquid_mass = liquid.mass_flows.get(name, 0.0)
            vaporized_mass += vapor_mass
            rows.append(
                {
                    "component": name,
                    "K": split.k_values.get(name, 0.0),
                    "feed_kg_h": feed_mass,
                    "vapor_kg_h": vapor_mass,
                    "liquid_kg_h": liquid_mass,
                    "vapor_recovery_pct": 100.0 * safe_divide(vapor_mass, feed_mass, 0.0),
                }
            )
        sensible = inlet.total_mass_flow() * 2.0 * (temperature_K - inlet.temperature_K)
        
        # Calculate latent heat using component-specific dH_vap where available
        latent = 0.0
        for name in molecular_moles:
            v_mass = vapor.mass_flows.get(name, 0.0)
            dh_v = components[name].dH_vap_kJ_kg or 300.0
            latent += v_mass * dh_v
            
        duty = sensible + latent
        return FlashResult(
            vapor=vapor,
            liquid=liquid,
            vapor_fraction=vapor_fraction,
            split_table=pd.DataFrame(rows),
            k_values=split.k_values,
            mode=split.mode,
            duty_kJ_h=duty,
        )


def diagnose_flash_result(result: FlashResult) -> FlashDiagnostic:
    """Diagnose flash split bounds, fallback and component distribution."""
    warnings: list[str] = []
    vf = max(min(float(result.vapor_fraction), 1.0), 0.0)
    phase_valid = abs(vf - float(result.vapor_fraction)) < 1.0e-12
    fallback = "none" if "Wilson" in result.mode or "thermo" in result.mode else str(result.mode)
    flags: dict[str, str] = {}
    table = result.split_table
    if not table.empty:
        for _, row in table.iterrows():
            comp = str(row.get("component"))
            recovery = float(row.get("vapor_recovery_pct", 0.0))
            if comp in {"hydrogen", "ethylene", "propylene"} and recovery < 1.0:
                flags[comp] = "light component low vapor recovery; check T/P/K values"
                warnings.append(f"{comp} vapor recovery is low for a light component.")
            elif comp in {"hexane", "heptane", "toluene", "ENB"} and recovery > 99.9 and vf < 0.95:
                flags[comp] = "heavy component high vapor recovery; verify flash conditions"
            else:
                flags[comp] = "distribution plausible"
    if result.vapor.polymer_mass_kg_h > 1.0e-12:
        flags["polymer_pseudo"] = "polymer in vapor is nonphysical"
        warnings.append("Polymer pseudo-component appeared in vapor stream.")
    else:
        flags["polymer_pseudo"] = "nonvolatile"
    return FlashDiagnostic(vf, phase_valid, 0.0, fallback, flags, warnings)
