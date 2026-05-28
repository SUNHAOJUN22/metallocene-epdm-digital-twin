"""Polymerization kinetics for metallocene EPDM/EPM solution process."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field

from .utils import R_GAS, TINY, clamp, positive, safe_divide
from .reaction_templates import template_with_fallback


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
    rates_mol_L_h: dict[str, float] = field(default_factory=dict)
    effective_rate_constants: dict[str, float] = field(default_factory=dict)
    concentration_basis: dict[str, float] = field(default_factory=dict)
    modifiers: dict[str, float] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


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
    rates = {"ethylene": k_E * C_E * Cstar, "propylene": k_P * C_P * Cstar, "ENB": k_D_eff * C_D * Cstar}
    k_eff = {"ethylene": k_E, "propylene": k_P, "ENB": k_D_eff}
    return RateResult(
        r_E_mol_L_h=rates["ethylene"],
        r_P_mol_L_h=rates["propylene"],
        r_ENB_mol_L_h=rates["ENB"],
        k_E=k_E,
        k_P=k_P,
        k_ENB_eff=k_D_eff,
        Cstar_mol_L=Cstar,
        activation_factor=0.0,
        pressure_factor_ENB=pf,
        ethylene_competition_factor=ef,
        rates_mol_L_h=rates,
        effective_rate_constants=k_eff,
        concentration_basis={"ethylene": C_E, "propylene": C_P, "ENB": C_D, "Cstar": Cstar},
        modifiers={"pressure_factor_ENB": pf, "ethylene_competition_factor": ef},
    )


def _template_rate_constant(monomer: str, temperature_K: float, params: KineticParameters) -> float:
    """Return a template-aware apparent rate constant for one monomer."""
    if monomer == "ethylene":
        return arrhenius(params.k_E_ref, params.Ea_E_J_mol, temperature_K, params.T_ref_K)
    if monomer == "propylene":
        return arrhenius(params.k_P_ref, params.Ea_P_J_mol, temperature_K, params.T_ref_K)
    if monomer == "ENB":
        return arrhenius(params.k_ENB_ref, params.Ea_ENB_J_mol, temperature_K, params.T_ref_K)
    # Generic fallback keeps the model executable but visibly uncalibrated.
    return arrhenius(params.k_P_ref, params.Ea_P_J_mol, temperature_K, params.T_ref_K)


def calculate_template_rates(
    template_id: str,
    concentrations: dict[str, float],
    catalyst_state: dict[str, float] | float,
    conditions: dict[str, float],
    parameters: KineticParameters | dict[str, Any] | None = None,
) -> RateResult:
    """Calculate apparent monomer rates from a reaction template.

    The EPDM template retains legacy `r_E/r_P/r_ENB` compatibility while the
    generic dictionaries are the canonical V4.5 output. Unknown monomers use a
    calibrated-fallback rate constant and return a warning instead of failing.
    """
    params = parameters if isinstance(parameters, KineticParameters) else KineticParameters(**(parameters or {}))
    template, warnings = template_with_fallback(template_id)
    temperature_K = float(conditions.get("temperature_K", conditions.get("T_K", params.T_ref_K)))
    pressure_MPa = float(conditions.get("pressure_MPa", 1.0))
    if isinstance(catalyst_state, dict):
        Cstar = positive(float(catalyst_state.get("Cstar_mol_L", catalyst_state.get("Cstar", 0.0))))
    else:
        Cstar = positive(float(catalyst_state))
    rates: dict[str, float] = {}
    k_eff: dict[str, float] = {}
    concentration_basis: dict[str, float] = {"Cstar": Cstar}
    modifiers: dict[str, float] = {}
    C_E = positive(concentrations.get("ethylene", 0.0))
    C_ENB = positive(concentrations.get("ENB", 0.0))
    pf = pressure_factor_enb(pressure_MPa, params)
    ef = ethylene_competition_factor(C_E, C_ENB, params)
    for monomer in template.monomers:
        C_i = positive(float(concentrations.get(monomer, 0.0)))
        k_i = _template_rate_constant(monomer, temperature_K, params)
        if monomer == "ENB":
            k_i *= pf * ef
        elif monomer not in {"ethylene", "propylene"}:
            warnings.append(f"Monomer {monomer} uses generic uncalibrated apparent rate fallback.")
        rates[monomer] = max(k_i * C_i * Cstar, 0.0)
        k_eff[monomer] = max(k_i, 0.0)
        concentration_basis[monomer] = C_i
    modifiers.update({"pressure_factor_ENB": pf, "ethylene_competition_factor": ef})
    return RateResult(
        r_E_mol_L_h=rates.get("ethylene", 0.0),
        r_P_mol_L_h=rates.get("propylene", 0.0),
        r_ENB_mol_L_h=rates.get("ENB", 0.0),
        k_E=k_eff.get("ethylene", 0.0),
        k_P=k_eff.get("propylene", 0.0),
        k_ENB_eff=k_eff.get("ENB", 0.0),
        Cstar_mol_L=Cstar,
        activation_factor=0.0,
        pressure_factor_ENB=pf,
        ethylene_competition_factor=ef,
        rates_mol_L_h={key: float(value) for key, value in rates.items()},
        effective_rate_constants={key: float(value) for key, value in k_eff.items()},
        concentration_basis=concentration_basis,
        modifiers=modifiers,
        warnings=warnings,
    )


def calculate_template_conversions(
    template_id: str,
    feed_moles: dict[str, float],
    consumed_moles: dict[str, float],
) -> dict[str, float]:
    """Return bounded fractional conversions for template monomers."""
    template, _ = template_with_fallback(template_id)
    conversions: dict[str, float] = {}
    for monomer in template.monomers:
        feed = positive(feed_moles.get(monomer, 0.0))
        consumed = min(positive(consumed_moles.get(monomer, 0.0)), feed)
        conversions[monomer] = clamp(safe_divide(consumed, feed, 0.0), 0.0, 1.0)
    return conversions


def calculate_template_polymer_segments(
    template_id: str,
    consumed_moles: dict[str, float],
) -> dict[str, float]:
    """Return polymer segment masses in kg/h from consumed mol/h."""
    template, _ = template_with_fallback(template_id)
    segments: dict[str, float] = {}
    for monomer in template.monomers:
        segment = template.polymer_segments.get(monomer, monomer)
        mw = positive(template.molecular_weights.get(monomer, 100.0), 0.0) or 100.0
        segments[segment] = segments.get(segment, 0.0) + positive(consumed_moles.get(monomer, 0.0)) * mw / 1000.0
    return segments


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
