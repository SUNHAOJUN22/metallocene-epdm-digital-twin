"""Polymerization kinetics for metallocene EPDM/EPM solution process."""

from __future__ import annotations

import math
from dataclasses import dataclass

from pydantic import BaseModel, Field

from .utils import R_GAS, TINY, clamp, positive, safe_divide


class KineticParameters(BaseModel):
    """Apparent kinetic and chain-transfer parameters.

    k_ref values are in L/mol/h and act on liquid monomer concentration and
    effective active center concentration. The numbers are deliberately
    apparent parameters and should be recalibrated with local experiments.
    """

    T_ref_K: float = 373.15
    k_E_ref: float = 3.6e6
    k_P_ref: float = 1.45e6
    k_ENB_ref: float = 4.0e6
    Ea_E_J_mol: float = 28000.0
    Ea_P_J_mol: float = 32000.0
    Ea_ENB_J_mol: float = 36000.0
    kd_h: float = 0.08
    K_Al: float = 300.0
    K_BHT: float = 1.0
    alpha_BHT: float = 0.15
    beta_P: float = 0.35
    beta_E: float = 0.01
    ktr_H2: float = 45.0
    Mw0: float = 620000.0
    dH_E_kJ_mol: float = -95.0
    dH_P_kJ_mol: float = -85.0
    dH_ENB_kJ_mol: float = -80.0


@dataclass
class RateResult:
    """Apparent reaction rates and modifiers."""

    r_E_mol_L_h: float
    r_P_mol_L_h: float
    r_ENB_mol_L_h: float
    k_E: float
    k_P: float
    k_ENB_eff: float
    Cstar_mol_L: float
    activation_factor: float
    pressure_factor_ENB: float
    ethylene_competition_factor: float


def arrhenius(k_ref: float, Ea_J_mol: float, temperature_K: float, T_ref_K: float = 373.15) -> float:
    """Return Arrhenius-adjusted apparent rate constant."""
    T = max(temperature_K, 1.0)
    exponent = -Ea_J_mol / R_GAS * (1.0 / T - 1.0 / T_ref_K)
    return k_ref * math.exp(clamp(exponent, -30.0, 30.0))


def activation_factor(AlTi_ratio: float, BHT_ratio: float, params: KineticParameters | None = None) -> float:
    """Return empirical active-center factor from Al/Ti and BHT ratios."""
    p = params or KineticParameters()
    AlTi = positive(AlTi_ratio)
    BHT = positive(BHT_ratio)
    f_AlTi = safe_divide(AlTi, p.K_Al + AlTi, 0.0)
    f_BHT = 1.0 + p.alpha_BHT * safe_divide(BHT, p.K_BHT + BHT, 0.0)
    return clamp(f_AlTi * f_BHT, 0.0, 2.0)


def active_center_concentration(
    catalyst_umol_h: float,
    liquid_volume_L_h: float,
    AlTi_ratio: float,
    BHT_ratio: float,
    tau_h: float,
    params: KineticParameters | None = None,
) -> float:
    """Estimate effective active center concentration in mol/L."""
    p = params or KineticParameters()
    feed_mol_h = positive(catalyst_umol_h) * 1.0e-6
    base_concentration = safe_divide(feed_mol_h, max(liquid_volume_L_h, TINY), 0.0)
    return base_concentration * activation_factor(AlTi_ratio, BHT_ratio, p) * math.exp(-p.kd_h * positive(tau_h))


def pressure_factor_enb(pressure_MPa: float, params: KineticParameters | None = None) -> float:
    """Return ENB insertion pressure penalty where pressure above 0.7 MPa is unfavorable."""
    p = params or KineticParameters()
    return safe_divide(1.0, 1.0 + p.beta_P * max(pressure_MPa - 0.7, 0.0), 1.0)


def ethylene_competition_factor(C_E: float, C_ENB: float, params: KineticParameters | None = None) -> float:
    """Return relative ENB insertion penalty from ethylene competition."""
    p = params or KineticParameters()
    ratio = safe_divide(positive(C_E), max(positive(C_ENB), TINY), 0.0)
    return safe_divide(1.0, 1.0 + p.beta_E * ratio, 1.0)


def reaction_rates(
    concentrations_mol_L: dict[str, float],
    Cstar_mol_L: float,
    temperature_K: float,
    pressure_MPa: float,
    params: KineticParameters | None = None,
) -> RateResult:
    """Calculate apparent EPDM monomer insertion rates in mol/L/h."""
    p = params or KineticParameters()
    C_E = positive(concentrations_mol_L.get("ethylene", 0.0))
    C_P = positive(concentrations_mol_L.get("propylene", 0.0))
    C_D = positive(concentrations_mol_L.get("ENB", 0.0))
    k_E = arrhenius(p.k_E_ref, p.Ea_E_J_mol, temperature_K, p.T_ref_K)
    k_P = arrhenius(p.k_P_ref, p.Ea_P_J_mol, temperature_K, p.T_ref_K)
    k_D = arrhenius(p.k_ENB_ref, p.Ea_ENB_J_mol, temperature_K, p.T_ref_K)
    pf = pressure_factor_enb(pressure_MPa, p)
    ef = ethylene_competition_factor(C_E, C_D, p)
    k_D_eff = k_D * pf * ef
    Cstar = positive(Cstar_mol_L)
    return RateResult(
        r_E_mol_L_h=k_E * C_E * Cstar,
        r_P_mol_L_h=k_P * C_P * Cstar,
        r_ENB_mol_L_h=k_D_eff * C_D * Cstar,
        k_E=k_E,
        k_P=k_P,
        k_ENB_eff=k_D_eff,
        Cstar_mol_L=Cstar,
        activation_factor=0.0,
        pressure_factor_ENB=pf,
        ethylene_competition_factor=ef,
    )


def estimate_molecular_weight(
    Mw0: float,
    hydrogen_concentration_mol_L: float,
    C2_wt: float,
    solids_wt: float,
    params: KineticParameters | None = None,
) -> float:
    """Estimate Mw from hydrogen chain transfer and composition modifiers."""
    p = params or KineticParameters()
    transfer = 1.0 + p.ktr_H2 * positive(hydrogen_concentration_mol_L)
    composition_factor = 1.0 + 0.20 * clamp((C2_wt - 55.0) / 25.0, -1.0, 1.0)
    solids_factor = 1.0 + 0.08 * clamp(solids_wt / 30.0, 0.0, 2.0)
    return clamp(Mw0 * composition_factor * solids_factor / max(transfer, 0.1), 50000.0, 2000000.0)
