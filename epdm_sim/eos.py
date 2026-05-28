"""Simplified cubic-EOS-inspired K-value helpers.

This is not a full rigorous phase-equilibrium package.  It adds a local PR/SRK
engineering mode between Wilson K and optional external thermo packages.
"""

from __future__ import annotations

import math
from functools import lru_cache
from typing import Any

import numpy as np

from .components import Component, load_components
from .utils import R_GAS, clamp, data_path, load_json


@lru_cache(maxsize=1)
def load_binary_interactions() -> dict[tuple[str, str], float]:
    """Load binary interaction parameters for cubic EOS mixing rules."""
    try:
        payload = load_json(data_path("binary_interactions.json"))
    except Exception:
        return {}
    interactions: dict[tuple[str, str], float] = {}
    for item in payload.get("pairs", []):
        try:
            a = str(item["component_i"])
            b = str(item["component_j"])
            kij = float(item.get("kij", 0.0))
            interactions[(a, b)] = kij
            interactions[(b, a)] = kij
        except Exception:
            continue
    return interactions


def binary_interaction(component_i: str, component_j: str, default: float = 0.0) -> float:
    """Return kij for a component pair, falling back to default when missing."""
    return float(load_binary_interactions().get((component_i, component_j), default))


def _alpha_and_m(component: Component, eos: str) -> tuple[float, float]:
    eos_key = eos.upper()
    if eos_key == "SRK":
        m = 0.480 + 1.574 * component.omega - 0.176 * component.omega**2
    else:
        m = 0.37464 + 1.54226 * component.omega - 0.26992 * component.omega**2
    return m, eos_key


def _pure_ab(component: Component, temperature_K: float, eos: str) -> tuple[float, float]:
    m, eos_key = _alpha_and_m(component, eos)
    Tr = max(temperature_K / max(component.Tc, 1.0), 1.0e-9)
    alpha = (1.0 + m * (1.0 - math.sqrt(Tr))) ** 2
    if eos_key == "SRK":
        a = 0.42748 * R_GAS**2 * component.Tc**2 / max(component.Pc, 1.0) * alpha
        b = 0.08664 * R_GAS * component.Tc / max(component.Pc, 1.0)
    else:
        a = 0.45724 * R_GAS**2 * component.Tc**2 / max(component.Pc, 1.0) * alpha
        b = 0.07780 * R_GAS * component.Tc / max(component.Pc, 1.0)
    return a, b


def cubic_z_roots(component: Component | str, temperature_K: float, pressure_Pa: float, eos: str = "PR") -> list[float]:
    """Return real compressibility-factor roots for a pure-component cubic EOS."""
    if isinstance(component, str):
        component = load_components()[component]
    T = max(float(temperature_K), 1.0)
    P = max(float(pressure_Pa), 1.0)
    a, b = _pure_ab(component, T, eos)
    A = a * P / max(R_GAS**2 * T**2, 1.0e-30)
    B = b * P / max(R_GAS * T, 1.0e-30)
    if eos.upper() == "SRK":
        coeffs = [1.0, -1.0, A - B - B**2, -A * B]
    else:
        coeffs = [1.0, -(1.0 - B), A - 3.0 * B**2 - 2.0 * B, -(A * B - B**2 - B**3)]
    roots = np.roots(coeffs)
    real_roots = sorted(float(root.real) for root in roots if abs(root.imag) < 1.0e-8 and root.real > B + 1.0e-10)
    return real_roots or [max(1.0, B + 1.0e-8)]


def fugacity_coefficient(component: Component | str, temperature_K: float, pressure_Pa: float, eos: str = "PR", phase: str = "vapor") -> float:
    """Return pure-component fugacity coefficient for selected EOS phase root."""
    details = cubic_eos_details(component, temperature_K, pressure_Pa, eos=eos)
    return float(details["phi_v"] if phase.lower().startswith("v") else details["phi_l"])


def cubic_eos_details(component: Component | str, temperature_K: float, pressure_Pa: float, eos: str = "PR") -> dict[str, float | str | list[float]]:
    """Return PR/SRK pure-component EOS diagnostics: Z, phi and K.

    The model uses pure-component cubic fugacity roots as an engineering
    enhancement over Wilson K.  For single-root states, the K value blends the
    fugacity ratio with the Wilson estimate to keep flash calculations robust.
    """
    if isinstance(component, str):
        component = load_components()[component]
    if component.type == "polymer":
        return {
            "component": component.name,
            "eos": eos.upper(),
            "Z_roots": [1.0],
            "Z_vapor": 1.0,
            "Z_liquid": 1.0,
            "phi_v": 1.0,
            "phi_l": 1.0e-12,
            "K": 1.0e-12,
            "A": 0.0,
            "B": 0.0,
            "applicability": "polymer nonvolatile pseudo-component",
        }
def cubic_eos_details(component: Component | str, temperature_K: float, pressure_Pa: float, eos: str = "PR") -> dict[str, float | str | list[float]]:
    """Return PR/SRK pure-component EOS diagnostics: Z, phi and K."""
    if isinstance(component, str):
        component = load_components()[component]
    if component.type == "polymer":
        return {
            "component": component.name,
            "eos": eos.upper(),
            "Z_roots": [1.0],
            "Z_vapor": 1.0,
            "Z_liquid": 1.0,
            "phi_v": 1.0,
            "phi_l": 1.0e-12,
            "K": 1.0e-12,
            "A": 0.0,
            "B": 0.0,
            "applicability": "polymer nonvolatile pseudo-component",
        }
    T = max(float(temperature_K), 1.0)
    P = max(float(pressure_Pa), 1.0)
    a, b = _pure_ab(component, T, eos)
    A = a * P / max(R_GAS**2 * T**2, 1.0e-30)
    B = b * P / max(R_GAS * T, 1.0e-30)
    roots = cubic_z_roots(component, T, P, eos)
    Z_l = min(roots)
    Z_v = max(roots)
    phi_l = _lnphi_to_phi(_ln_phi(Z_l, A, B, eos))
    phi_v = _lnphi_to_phi(_ln_phi(Z_v, A, B, eos))
    wilson = _wilson_k(component, T, P)
    if len(roots) > 1 and phi_v > 0.0:
        K = phi_l / phi_v
    else:
        K = wilson
    if component.name == "hydrogen":
        K *= 1.5
    K = clamp(K, 1.0e-12, 1.0e12)
    return {
        "component": component.name,
        "eos": eos.upper(),
        "Z_roots": roots,
        "Z_vapor": Z_v,
        "Z_liquid": Z_l,
        "phi_v": phi_v,
        "phi_l": phi_l,
        "K": K,
        "A": A,
        "B": B,
        "applicability": "local cubic EOS engineering estimate",
    }


def mixture_parameters(
    z_molar: dict[str, float], 
    temperature_K: float, 
    eos: str = "PR"
) -> tuple[float, float]:
    """Calculate mixture 'a' and 'b' parameters using VdW one-fluid mixing rules."""
    comps = load_components()
    names = [n for n, v in z_molar.items() if v > 0 and n in comps]
    if not names:
        return 0.0, 0.0
    
    z = np.array([z_molar[n] for n in names])
    z = z / np.sum(z)
    
    a_pure = []
    b_pure = []
    for n in names:
        ai, bi = _pure_ab(comps[n], temperature_K, eos)
        a_pure.append(ai)
        b_pure.append(bi)
        
    a_pure = np.array(a_pure)
    b_pure = np.array(b_pure)
    kij = load_binary_interactions()
    
    # b_mix = sum(z_i * b_i)
    b_mix = np.sum(z * b_pure)
    
    # a_mix = sum_i sum_j (z_i * z_j * sqrt(a_i * a_j) * (1 - kij))
    a_mix = 0.0
    for i in range(len(names)):
        for j in range(len(names)):
            k = kij.get((names[i], names[j]), 0.0)
            a_mix += z[i] * z[j] * math.sqrt(max(a_pure[i] * a_pure[j], 0.0)) * (1.0 - k)
            
    return float(a_mix), float(b_mix)


def mixture_ln_phi(
    z_molar: dict[str, float],
    temperature_K: float,
    pressure_Pa: float,
    eos: str = "PR",
    phase: str = "vapor"
) -> dict[str, float]:
    """Calculate mixture fugacity coefficients for each component."""
    comps = load_components()
    names = [n for n, v in z_molar.items() if v > 0 and n in comps]
    if not names:
        return {}
        
    a_mix, b_mix = mixture_parameters(z_molar, temperature_K, eos)
    A = a_mix * pressure_Pa / (R_GAS * temperature_K)**2
    B = b_mix * pressure_Pa / (R_GAS * temperature_K)
    
    # Solve Z for mixture
    if eos.upper() == "SRK":
        coeffs = [1.0, -1.0, A - B - B**2, -A * B]
    else:
        coeffs = [1.0, -(1.0 - B), A - 3.0 * B**2 - 2.0 * B, -(A * B - B**2 - B**3)]
    
    roots = np.roots(coeffs)
    real_roots = sorted(float(root.real) for root in roots if abs(root.imag) < 1.0e-8 and root.real > B + 1.0e-10)
    Z = max(real_roots) if phase.lower().startswith("v") else min(real_roots)
    
    # Calculate partial derivatives (simplified VdW rules)
    ln_phi = {}
    z_list = np.array([z_molar[n] for n in names])
    z_list = z_list / np.sum(z_list)
    
    a_pure = np.array([_pure_ab(comps[n], temperature_K, eos)[0] for n in names])
    b_pure = np.array([_pure_ab(comps[n], temperature_K, eos)[1] for n in names])
    
    kij = load_binary_interactions()
    
    for i, name in enumerate(names):
        # bi / b_mix
        term_b = b_pure[i] / b_mix
        
        # 1/a_mix * sum_j (z_j * sqrt(a_i * a_j) * (1 - kij))
        sum_term = 0.0
        for j in range(len(names)):
            k = kij.get((names[i], names[j]), 0.0)
            sum_term += z_list[j] * math.sqrt(max(a_pure[i] * a_pure[j], 0.0)) * (1.0 - k)
        term_a = 2.0 * sum_term / a_mix
        
        if eos.upper() == "SRK":
            ln_phi_i = term_b * (Z - 1.0) - math.log(max(Z - B, 1.0e-15)) - A / B * (term_a - term_b) * math.log(max(1.0 + B / Z, 1.0e-15))
        else:
            sqrt2 = math.sqrt(2.0)
            log_term = math.log(max((Z + (1.0 + sqrt2) * B) / (Z + (1.0 - sqrt2) * B), 1.0e-15))
            ln_phi_i = term_b * (Z - 1.0) - math.log(max(Z - B, 1.0e-15)) - A / (2.0 * sqrt2 * B) * (term_a - term_b) * log_term
            
        ln_phi[name] = float(ln_phi_i)
        
    return ln_phi


def cubic_eos_mixture_k_values(
    z_molar: dict[str, float],
    temperature_K: float,
    pressure_Pa: float,
    eos: str = "PR"
) -> dict[str, float]:
    """Calculate mixture K-values using fugacity coefficient ratios."""
    phi_v = mixture_ln_phi(z_molar, temperature_K, pressure_Pa, eos, "vapor")
    phi_l = mixture_ln_phi(z_molar, temperature_K, pressure_Pa, eos, "liquid")
    
    k_values = {}
    for name in phi_v:
        k = math.exp(clamp(phi_l[name] - phi_v[name], -40.0, 40.0))
        k_values[name] = clamp(k, 1.0e-12, 1.0e12)
        
    return k_values




def _ln_phi(Z: float, A: float, B: float, eos: str) -> float:
    """Return ln(phi) for pure PR/SRK EOS."""
    Z = max(float(Z), B + 1.0e-12)
    B = max(float(B), 1.0e-14)
    if eos.upper() == "SRK":
        return Z - 1.0 - math.log(max(Z - B, 1.0e-30)) - A / B * math.log(max(1.0 + B / Z, 1.0e-30))
    sqrt2 = math.sqrt(2.0)
    arg = (Z + (1.0 + sqrt2) * B) / max(Z + (1.0 - sqrt2) * B, 1.0e-30)
    return Z - 1.0 - math.log(max(Z - B, 1.0e-30)) - A / (2.0 * sqrt2 * B) * math.log(max(arg, 1.0e-30))


def _lnphi_to_phi(ln_phi: float) -> float:
    return math.exp(clamp(float(ln_phi), -80.0, 80.0))


def _wilson_k(component: Component, temperature_K: float, pressure_Pa: float) -> float:
    P = max(float(pressure_Pa), 1.0)
    ln_k = math.log(max(component.Pc, 1.0) / P) + 5.373 * (1.0 + component.omega) * (1.0 - component.Tc / max(temperature_K, 1.0))
    wilson = math.exp(clamp(ln_k, -40.0, 40.0))
    if component.name == "hydrogen":
        wilson *= 30.0
    elif component.name == "ethylene":
        wilson *= 4.0
    elif component.name == "propylene":
        wilson *= 1.8
    elif component.name == "ENB":
        wilson *= 0.35
    return wilson


def cubic_eos_k_value(component: Component | str, temperature_K: float, pressure_Pa: float, eos: str = "PR") -> float:
    """Return a PR/SRK cubic-EOS K value with robust Wilson fallback."""
    if isinstance(component, str):
        component = load_components()[component]
    return float(cubic_eos_details(component, temperature_K, pressure_Pa, eos=eos)["K"])


def eos_k_values(names: list[str], temperature_K: float, pressure_Pa: float, eos: str = "PR") -> dict[str, float]:
    """Return K values for component names using the simplified cubic EOS mode."""
    comps = load_components()
    return {name: cubic_eos_k_value(comps[name], temperature_K, pressure_Pa, eos) for name in names if name in comps}


def eos_details_table(names: list[str], temperature_K: float, pressure_Pa: float, eos: str = "PR") -> list[dict[str, Any]]:
    """Return EOS diagnostics rows for UI/reporting."""
    comps = load_components()
    rows = []
    for name in names:
        if name not in comps:
            continue
        details = cubic_eos_details(comps[name], temperature_K, pressure_Pa, eos=eos)
        rows.append({key: value for key, value in details.items() if key != "Z_roots"} | {"Z_roots": ",".join(f"{z:.4g}" for z in details["Z_roots"])})
    return rows


def k_value_comparison(names: list[str], temperature_K: float, pressure_Pa: float) -> dict[str, dict[str, float]]:
    """Compare Wilson, PR and SRK K values for components."""
    comps = load_components()
    rows: dict[str, dict[str, float]] = {}
    for name in names:
        comp = comps.get(name)
        if comp is None:
            continue
        rows[name] = {
            "Wilson": clamp(_wilson_k(comp, temperature_K, pressure_Pa), 1.0e-12, 1.0e12),
            "PR": cubic_eos_k_value(comp, temperature_K, pressure_Pa, "PR"),
            "SRK": cubic_eos_k_value(comp, temperature_K, pressure_Pa, "SRK"),
        }
    return rows
