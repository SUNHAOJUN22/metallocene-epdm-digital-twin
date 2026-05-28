"""Mixture fluid properties, viscosity calibration and pipe hydraulics."""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pydantic import BaseModel

from .components import Component, load_components
from .streams import Stream
from .thermo import wilson_k_value
from .utils import R_GAS, TINY, data_path, positive, safe_divide


class ViscosityModelParameters(BaseModel):
    """Polymer solution viscosity model parameters."""

    A_mu: float = 8.0
    B_mu: float = 15.0
    alpha_Mw: float = 0.6
    E_mu_J_mol: float = 12000.0
    T_ref_K: float = 298.15


@dataclass
class FluidPropertyResult:
    """Calculated fluid property result for a process stream."""

    stream_name: str
    temperature_K: float
    pressure_Pa: float
    mixture_mw_g_mol: float
    liquid_density_kg_m3: float
    gas_density_kg_m3: float
    Cp_liq_kJ_kgK: float
    Cp_gas_kJ_kgK: float
    thermal_conductivity_W_mK: float
    dynamic_viscosity_Pa_s: float
    kinematic_viscosity_m2_s: float
    vapor_pressure_Pa: float
    solids_wt: float
    polymer_solution_viscosity_index: float
    fouling_risk_index: float
    fouling_risk: str
    viscosity_parameters: dict[str, float]

    def as_dataframe(self) -> pd.DataFrame:
        """Return the fluid property result as a report table."""
        rows = [
            ("mixture molecular weight", self.mixture_mw_g_mol, "g/mol"),
            ("liquid density", self.liquid_density_kg_m3, "kg/m3"),
            ("gas density", self.gas_density_kg_m3, "kg/m3"),
            ("liquid Cp", self.Cp_liq_kJ_kgK, "kJ/kg/K"),
            ("gas Cp", self.Cp_gas_kJ_kgK, "kJ/kg/K"),
            ("thermal conductivity", self.thermal_conductivity_W_mK, "W/m/K"),
            ("dynamic viscosity", self.dynamic_viscosity_Pa_s, "Pa.s"),
            ("kinematic viscosity", self.kinematic_viscosity_m2_s, "m2/s"),
            ("vapor pressure", self.vapor_pressure_Pa, "Pa"),
            ("solids content", self.solids_wt, "wt%"),
            ("polymer solution viscosity index", self.polymer_solution_viscosity_index, "-"),
            ("fouling risk index", self.fouling_risk_index, "-"),
            ("fouling risk", self.fouling_risk, "-"),
        ]
        return pd.DataFrame(rows, columns=["property", "value", "unit"])


@dataclass
class PipeHydraulicsResult:
    """Pipe pressure drop and pumping power result."""

    Reynolds: float
    flow_regime: str
    friction_factor: float
    pressure_drop_kPa: float
    pump_power_kW: float
    velocity_m_s: float
    volumetric_flow_m3_h: float
    transport_risk: str

    def as_dataframe(self) -> pd.DataFrame:
        """Return pressure-drop result as a table."""
        return pd.DataFrame(
            [
                ("Reynolds number", self.Reynolds, "-"),
                ("flow regime", self.flow_regime, "-"),
                ("Darcy friction factor", self.friction_factor, "-"),
                ("pressure drop", self.pressure_drop_kPa, "kPa"),
                ("pump power", self.pump_power_kW, "kW"),
                ("velocity", self.velocity_m_s, "m/s"),
                ("transport risk", self.transport_risk, "-"),
            ],
            columns=["item", "value", "unit"],
        )


def _component_value(component: Component, attr: str, fallback: str, default: float) -> float:
    """Read a component fluid-property value with fallback to legacy names."""
    value = getattr(component, attr, None)
    if value is None:
        value = getattr(component, fallback, None)
    return positive(value if value is not None else default, 0.0)


def load_fluid_property_calibration() -> pd.DataFrame:
    """Load optional measured fluid property calibration data."""
    path = data_path("fluid_property_calibration.csv")
    if not Path(path).exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


@lru_cache(maxsize=1)
def calibrate_viscosity_parameters() -> ViscosityModelParameters:
    """Fit A_mu, B_mu and alpha_Mw if measured calibration data exists."""
    defaults = ViscosityModelParameters()
    df = load_fluid_property_calibration()
    needed = {"temperature_C", "solids_wt", "Mw", "viscosity_Pa_s"}
    if df.empty or not needed.issubset(df.columns):
        return defaults
    df = df.dropna(subset=list(needed))
    df = df[(df["viscosity_Pa_s"] > 0) & (df["Mw"] > 0)]
    if len(df) < 4:
        return defaults
    try:
        solids_fraction = df["solids_wt"].to_numpy(dtype=float) / 100.0
        mw_term = np.log(df["Mw"].to_numpy(dtype=float) / 300000.0)
        temperature_K = df["temperature_C"].to_numpy(dtype=float) + 273.15
        base_mu = 0.00030 * np.exp(defaults.E_mu_J_mol / R_GAS * (1.0 / temperature_K - 1.0 / defaults.T_ref_K))
        y = np.log(df["viscosity_Pa_s"].to_numpy(dtype=float) / np.maximum(base_mu, TINY))
        X = np.column_stack([solids_fraction, solids_fraction**2, mw_term])
        coeffs, *_ = np.linalg.lstsq(X, y, rcond=None)
        if not np.all(np.isfinite(coeffs)):
            return defaults
        return ViscosityModelParameters(
            A_mu=float(np.clip(coeffs[0], 0.0, 40.0)),
            B_mu=float(np.clip(coeffs[1], 0.0, 80.0)),
            alpha_Mw=float(np.clip(coeffs[2], 0.0, 2.0)),
            E_mu_J_mol=defaults.E_mu_J_mol,
            T_ref_K=defaults.T_ref_K,
        )
    except Exception:
        return defaults


def mixture_molecular_weight(stream: Stream, components: dict[str, Component] | None = None) -> float:
    """Calculate molecular mixture MW in g/mol from molecular mole fractions."""
    comps = components or load_components()
    total_moles = stream.total_molar_flow()
    if total_moles <= TINY:
        return 0.0
    return sum(positive(flow) * comps[name].MW for name, flow in stream.molar_flows.items() if name in comps) / total_moles


def liquid_density(stream: Stream, components: dict[str, Component] | None = None) -> float:
    """Calculate liquid mixture density by volume additivity."""
    comps = components or load_components()
    total_mass = stream.total_mass_flow()
    volume_m3_h = 0.0
    for name, mass in stream.mass_flows.items():
        if name in comps:
            rho = _component_value(comps[name], "liquid_density_kg_m3", "density_liq", 750.0)
            volume_m3_h += positive(mass) / max(rho, TINY)
    if stream.polymer_mass_kg_h > 0:
        polymer = comps.get("polymer_pseudo") or comps.get("polymer_EPDM")
        rho_p = _component_value(polymer, "density_kg_m3", "density_liq", 860.0) if polymer else 860.0
        volume_m3_h += stream.polymer_mass_kg_h / max(rho_p, TINY)
    return safe_divide(total_mass, volume_m3_h, 750.0)


def mixture_cp(stream: Stream, phase: str = "liquid", components: dict[str, Component] | None = None) -> float:
    """Calculate mass-weighted mixture heat capacity in kJ/kg/K."""
    comps = components or load_components()
    total_mass = stream.total_mass_flow()
    if total_mass <= TINY:
        return 2.0
    cp_sum = 0.0
    for name, mass in stream.mass_flows.items():
        if name not in comps:
            continue
        if phase == "gas":
            cp = _component_value(comps[name], "Cp_gas_kJ_kgK", "Cp_gas", 1.5)
        else:
            cp = _component_value(comps[name], "Cp_liq_kJ_kgK", "Cp_liq", 2.0)
        cp_sum += positive(mass) * cp
    if stream.polymer_mass_kg_h > 0:
        polymer = comps.get("polymer_pseudo") or comps.get("polymer_EPDM")
        cp_p = _component_value(polymer, "Cp_solid_kJ_kgK", "Cp_liq", 1.9) if polymer else 1.9
        cp_sum += stream.polymer_mass_kg_h * cp_p
    return cp_sum / total_mass


def gas_density(stream: Stream, temperature_K: float, pressure_Pa: float, components: dict[str, Component] | None = None) -> float:
    """Calculate gas density by ideal gas equation in kg/m3."""
    mw_g_mol = mixture_molecular_weight(stream, components)
    return pressure_Pa * (mw_g_mol / 1000.0) / (R_GAS * max(temperature_K, 1.0))


def solvent_log_mixed_viscosity(
    stream: Stream,
    temperature_K: float,
    components: dict[str, Component] | None = None,
    params: ViscosityModelParameters | None = None,
) -> float:
    """Calculate solvent/monomer viscosity by mole-fraction logarithmic mixing."""
    comps = components or load_components()
    p = params or calibrate_viscosity_parameters()
    mole_fracs = stream.mole_fractions()
    ln_mu = 0.0
    denom = 0.0
    for name, x in mole_fracs.items():
        if name not in comps:
            continue
        mu = _component_value(comps[name], "viscosity_Pa_s", "viscosity_Pa_s", 0.0003)
        ln_mu += positive(x) * math.log(max(mu, 1.0e-8))
        denom += positive(x)
    if denom <= TINY:
        mu_ref = 0.0003
    else:
        mu_ref = math.exp(ln_mu / denom)
    return mu_ref * math.exp(p.E_mu_J_mol / R_GAS * (1.0 / max(temperature_K, 1.0) - 1.0 / p.T_ref_K))


def polymer_solution_viscosity(
    stream: Stream,
    temperature_K: float,
    Mw: float,
    components: dict[str, Component] | None = None,
    params: ViscosityModelParameters | None = None,
    solids_wt_override: float | None = None,
) -> float:
    """Calculate dynamic viscosity of polymer solution in Pa.s."""
    p = params or calibrate_viscosity_parameters()
    solvent_mu = solvent_log_mixed_viscosity(stream, temperature_K, components, p)
    solids_fraction = max((stream.solids_wt if solids_wt_override is None else solids_wt_override) / 100.0, 0.0)
    polymer_factor = math.exp(p.A_mu * solids_fraction + p.B_mu * solids_fraction**2)
    mw_factor = (max(Mw, 50000.0) / 300000.0) ** p.alpha_Mw
    return solvent_mu * polymer_factor * mw_factor


def thermal_conductivity(stream: Stream, components: dict[str, Component] | None = None) -> float:
    """Calculate mass-weighted thermal conductivity in W/m/K."""
    comps = components or load_components()
    total_mass = stream.total_mass_flow()
    if total_mass <= TINY:
        return 0.12
    k_sum = 0.0
    for name, mass in stream.mass_flows.items():
        if name in comps:
            k_i = _component_value(comps[name], "thermal_conductivity_W_mK", "thermal_conductivity_W_mK", 0.12)
            k_sum += positive(mass) * k_i
    if stream.polymer_mass_kg_h > 0:
        polymer = comps.get("polymer_pseudo") or comps.get("polymer_EPDM")
        k_p = _component_value(polymer, "thermal_conductivity_W_mK", "thermal_conductivity_W_mK", 0.20) if polymer else 0.20
        k_sum += stream.polymer_mass_kg_h * k_p
    k_mix = k_sum / total_mass
    return k_mix * (1.0 - 0.15 * min(stream.solids_wt / 100.0, 0.6))


def mixture_vapor_pressure(stream: Stream, temperature_K: float, pressure_Pa: float, components: dict[str, Component] | None = None) -> float:
    """Estimate mixture vapor pressure by mole-fraction weighted Wilson Psat."""
    comps = components or load_components()
    mole_fracs = stream.mole_fractions()
    return sum(
        positive(x) * wilson_k_value(comps[name], temperature_K, pressure_Pa) * pressure_Pa
        for name, x in mole_fracs.items()
        if name in comps and comps[name].type != "polymer"
    )


def fluid_fouling_risk(solids_wt: float, viscosity_Pa_s: float, Mw: float, kinematic_viscosity_m2_s: float) -> tuple[float, str]:
    """Estimate gel solution fouling/transport risk index."""
    viscosity_index = (positive(solids_wt) / 20.0) ** 2 * (max(Mw, 50000.0) / 300000.0) ** 0.6
    viscosity_index *= max(viscosity_Pa_s / 0.001, 0.05) ** 0.4
    viscosity_index *= max(kinematic_viscosity_m2_s / 1.0e-6, 0.1) ** 0.15
    if viscosity_index < 1.0:
        return viscosity_index, "low"
    if viscosity_index < 3.0:
        return viscosity_index, "medium"
    return viscosity_index, "high"


def calculate_fluid_properties(stream: Stream, Mw: float, temperature_K: float | None = None, pressure_Pa: float | None = None) -> FluidPropertyResult:
    """Calculate core mixture fluid properties for a stream."""
    comps = load_components()
    T = temperature_K or stream.temperature_K
    P = pressure_Pa or stream.pressure_Pa
    params = calibrate_viscosity_parameters()
    mw_mix = mixture_molecular_weight(stream, comps)
    rho_liq = liquid_density(stream, comps)
    rho_gas = gas_density(stream, T, P, comps)
    cp_liq = mixture_cp(stream, "liquid", comps)
    cp_gas = mixture_cp(stream, "gas", comps)
    k_mix = thermal_conductivity(stream, comps)
    mu = polymer_solution_viscosity(stream, T, Mw, comps, params)
    nu = safe_divide(mu, rho_liq, 0.0)
    vapor_pressure = mixture_vapor_pressure(stream, T, P, comps)
    viscosity_index = safe_divide(mu, 0.001, 0.0) * (max(stream.solids_wt, 0.0) / 10.0 + 0.1)
    fouling_index, fouling_level = fluid_fouling_risk(stream.solids_wt, mu, Mw, nu)
    return FluidPropertyResult(
        stream_name=stream.name,
        temperature_K=T,
        pressure_Pa=P,
        mixture_mw_g_mol=mw_mix,
        liquid_density_kg_m3=rho_liq,
        gas_density_kg_m3=rho_gas,
        Cp_liq_kJ_kgK=cp_liq,
        Cp_gas_kJ_kgK=cp_gas,
        thermal_conductivity_W_mK=k_mix,
        dynamic_viscosity_Pa_s=mu,
        kinematic_viscosity_m2_s=nu,
        vapor_pressure_Pa=vapor_pressure,
        solids_wt=stream.solids_wt,
        polymer_solution_viscosity_index=viscosity_index,
        fouling_risk_index=fouling_index,
        fouling_risk=fouling_level,
        viscosity_parameters={
            "A_mu": params.A_mu,
            "B_mu": params.B_mu,
            "alpha_Mw": params.alpha_Mw,
            "E_mu_J_mol": params.E_mu_J_mol,
        },
    )


def estimate_stream_volumetric_flow_m3_h(stream: Stream, density_kg_m3: float) -> float:
    """Estimate volumetric flow rate from stream mass flow and density."""
    return safe_divide(stream.total_mass_flow(), max(density_kg_m3, TINY), 0.0)


def calculate_pipe_hydraulics(
    liquid_density_kg_m3: float,
    dynamic_viscosity_Pa_s: float,
    volumetric_flow_m3_h: float,
    pipe_length_m: float,
    pipe_diameter_m: float,
    roughness_m: float = 0.0,
    pump_efficiency: float = 0.65,
) -> PipeHydraulicsResult:
    """Calculate Darcy-Weisbach pressure drop and pump power."""
    D = max(pipe_diameter_m, 1.0e-5)
    area = math.pi * D**2 / 4.0
    q_m3_s = positive(volumetric_flow_m3_h) / 3600.0
    velocity = safe_divide(q_m3_s, area, 0.0)
    rho = max(liquid_density_kg_m3, 1.0)
    mu = max(dynamic_viscosity_Pa_s, 1.0e-8)
    Re = rho * velocity * D / mu
    if Re < 2100.0:
        friction = safe_divide(64.0, max(Re, TINY), 0.0)
        regime = "laminar"
    else:
        friction = 0.3164 / max(Re, TINY) ** 0.25
        if roughness_m > 0.0:
            friction *= 1.0 + min(roughness_m / D * 50.0, 0.5)
        regime = "turbulent"
    deltaP_Pa = friction * positive(pipe_length_m) / D * rho * velocity**2 / 2.0
    pump_power_kW = deltaP_Pa * q_m3_s / max(pump_efficiency, 0.05) / 1000.0
    if Re < 100.0 and deltaP_Pa > 100000.0:
        risk = "输送困难/挂胶风险"
    elif deltaP_Pa > 200000.0:
        risk = "压降偏高"
    else:
        risk = "normal"
    return PipeHydraulicsResult(
        Reynolds=Re,
        flow_regime=regime,
        friction_factor=friction,
        pressure_drop_kPa=deltaP_Pa / 1000.0,
        pump_power_kW=pump_power_kW,
        velocity_m_s=velocity,
        volumetric_flow_m3_h=volumetric_flow_m3_h,
        transport_risk=risk,
    )
