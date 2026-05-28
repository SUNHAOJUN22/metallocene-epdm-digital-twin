"""Simplified thermodynamic models and optional thermo package detection."""

from __future__ import annotations

import importlib.util
import math
from dataclasses import dataclass

import numpy as np
from scipy.optimize import brentq

from .components import Component, load_components
from .eos import eos_k_values
from .utils import TINY, clamp, positive


def thermo_package_available() -> bool:
    """Return True if the optional thermo package can be imported."""
    return importlib.util.find_spec("thermo") is not None


def wilson_k_value(component: Component, temperature_K: float, pressure_Pa: float) -> float:
    """Estimate K value using Wilson correlation.

    Wilson: ln(K) = ln(Pc/P) + 5.373(1+omega)(1 - Tc/T)
    """
    if component.type == "polymer":
        return 1.0e-12
    T = max(temperature_K, 1.0)
    P = max(pressure_Pa, 1.0)
    try:
        ln_k = math.log(component.Pc / P) + 5.373 * (1.0 + component.omega) * (1.0 - component.Tc / T)
        k = math.exp(clamp(ln_k, -40.0, 40.0))
    except (OverflowError, ValueError):
        k = 1.0
    if component.name == "hydrogen":
        k *= 30.0
    elif component.name == "ethylene":
        k *= 4.0
    elif component.name == "propylene":
        k *= 1.8
    elif component.name == "ENB":
        k *= 0.35
    return clamp(k, 1.0e-12, 1.0e12)


def rachford_rice_residual(vapor_fraction: float, z: np.ndarray, k_values: np.ndarray) -> float:
    """Rachford-Rice residual for a vapor fraction."""
    denom = 1.0 + vapor_fraction * (k_values - 1.0)
    denom = np.maximum(denom, TINY)
    return float(np.sum(z * (k_values - 1.0) / denom))


def solve_rachford_rice(z: np.ndarray, k_values: np.ndarray) -> float:
    """Solve Rachford-Rice equation and return vapor fraction in [0, 1]."""
    z = np.asarray(z, dtype=float)
    k_values = np.asarray(k_values, dtype=float)
    if z.size == 0 or np.sum(z) <= TINY:
        return 0.0
    z = z / np.sum(z)
    k_values = np.clip(k_values, 1.0e-12, 1.0e12)
    f0 = rachford_rice_residual(0.0, z, k_values)
    f1 = rachford_rice_residual(1.0, z, k_values)
    if f0 <= 0.0:
        return 0.0
    if f1 >= 0.0:
        return 1.0
    try:
        return float(brentq(lambda v: rachford_rice_residual(v, z, k_values), 0.0, 1.0, xtol=1.0e-12))
    except ValueError:
        return float(clamp(-f0 / max(f1 - f0, TINY), 0.0, 1.0))


@dataclass
class FlashSplit:
    """Flash calculation result."""

    vapor_fraction: float
    x: dict[str, float]
    y: dict[str, float]
    k_values: dict[str, float]
    mode: str


class ThermoEngine:
    """Thermodynamics facade with a stable simple-mode fallback."""

    def __init__(self, mode: str = "Simple Wilson K", components: dict[str, Component] | None = None):
        self.requested_mode = mode
        self.components = components or load_components()
        if mode.startswith("thermo") and thermo_package_available():
            self.mode = "thermo-backed"
        elif mode.upper().startswith("PR"):
            self.mode = "PR simplified EOS"
        elif mode.upper().startswith("SRK"):
            self.mode = "SRK simplified EOS"
        else:
            self.mode = "Simple Wilson K"
        self._thermo_aliases = {
            "ethylene": "ethylene",
            "propylene": "propylene",
            "ENB": "5-ethylidene-2-norbornene",
            "hydrogen": "hydrogen",
            "hexane": "hexane",
            "heptane": "heptane",
            "toluene": "toluene",
            "custom_solvent": "hexane",
        }

    def k_values(self, names: list[str], temperature_K: float, pressure_Pa: float, z_moles: dict[str, float] | None = None) -> dict[str, float]:
        """Return K values for selected component names.
        
        If z_moles is provided and mode is EOS, use mixture-aware fugacity coefficients.
        """
        if self.mode == "thermo-backed":
            return self._thermo_k_values(names, temperature_K, pressure_Pa)
        
        if (self.mode.startswith("PR") or self.mode.startswith("SRK")) and z_moles:
            from .eos import cubic_eos_mixture_k_values
            eos_type = "PR" if self.mode.startswith("PR") else "SRK"
            return cubic_eos_mixture_k_values(z_moles, temperature_K, pressure_Pa, eos_type)
            
        if self.mode.startswith("PR"):
            return eos_k_values(names, temperature_K, pressure_Pa, "PR")
        if self.mode.startswith("SRK"):
            return eos_k_values(names, temperature_K, pressure_Pa, "SRK")
        return {
            name: wilson_k_value(self.components[name], temperature_K, pressure_Pa)
            for name in names
            if name in self.components
        }

    def _thermo_k_values(self, names: list[str], temperature_K: float, pressure_Pa: float) -> dict[str, float]:
        """Try optional thermo package K values and fall back to Wilson values."""
        try:
            from thermo import Chemical
        except Exception:
            self.mode = "Simple Wilson K"
            return {
                name: wilson_k_value(self.components[name], temperature_K, pressure_Pa)
                for name in names
                if name in self.components
            }
        k_map: dict[str, float] = {}
        for name in names:
            component = self.components[name]
            if component.type == "polymer":
                k_map[name] = 1.0e-12
                continue
            try:
                alias = self._thermo_aliases.get(name, name)
                chemical = Chemical(alias, T=temperature_K, P=pressure_Pa)
                psat = getattr(chemical, "Psat", None)
                if psat is None or psat <= 0.0:
                    raise ValueError("thermo Psat unavailable")
                k_map[name] = clamp(float(psat) / max(pressure_Pa, 1.0), 1.0e-12, 1.0e12)
            except Exception:
                k_map[name] = wilson_k_value(component, temperature_K, pressure_Pa)
        return k_map

    def flash(self, z_moles: dict[str, float], temperature_K: float, pressure_Pa: float) -> FlashSplit:
        """Perform an isothermal-isobaric flash for molecular components."""
        names = [name for name, flow in z_moles.items() if positive(flow) > TINY and name in self.components]
        if not names:
            return FlashSplit(0.0, {}, {}, {}, self.mode)
        z = np.array([positive(z_moles[name]) for name in names], dtype=float)
        z = z / np.sum(z)
        k_map = self.k_values(names, temperature_K, pressure_Pa, z_moles=z_moles)
        k = np.array([k_map[name] for name in names], dtype=float)
        vapor_fraction = solve_rachford_rice(z, k)
        denom = np.maximum(1.0 + vapor_fraction * (k - 1.0), TINY)
        x = z / denom
        y = k * x
        if np.sum(x) > TINY:
            x = x / np.sum(x)
        if np.sum(y) > TINY:
            y = y / np.sum(y)
        return FlashSplit(
            vapor_fraction=float(clamp(vapor_fraction, 0.0, 1.0)),
            x={name: float(value) for name, value in zip(names, x)},
            y={name: float(value) for name, value in zip(names, y)},
            k_values=k_map,
            mode=self.mode,
        )


def mixture_cp_liq(mass_flows: dict[str, float], components: dict[str, Component] | None = None) -> float:
    """Return mass-weighted liquid heat capacity in kJ/kg/K."""
    comps = components or load_components()
    total = sum(positive(value) for value in mass_flows.values())
    if total <= TINY:
        return 2.0
    cp = 0.0
    for name, mass in mass_flows.items():
        if name in comps:
            cp += positive(mass) * comps[name].Cp_liq
    return cp / total
