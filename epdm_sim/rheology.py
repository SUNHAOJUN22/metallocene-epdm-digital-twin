"""Unified Newtonian and non-Newtonian rheology models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import math
import pandas as pd

from .dimensioned import ensure_temperature_K, ensure_viscosity_Pa_s
from .utils import R_GAS, clamp, positive


@dataclass(frozen=True)
class RheologyParameters:
    """Rheology parameter set for polymer solution apparent viscosity."""

    model: str = "EPDM empirical solution viscosity"
    A_mu: float = 8.0
    B_mu: float = 15.0
    alpha_Mw: float = 0.6
    E_mu_J_mol: float = 12000.0
    T_ref_K: float = 298.15
    mu_solvent_ref_Pa_s: float = 3.0e-4
    power_law_n: float = 0.72
    reference_shear_rate_s: float = 10.0
    carreau_mu_inf_ratio: float = 0.08
    carreau_lambda_s: float = 1.2
    carreau_a: float = 2.0
    carreau_n: float = 0.62


@dataclass(frozen=True)
class RheologyResult:
    """Rheology calculation output."""

    dynamic_viscosity_Pa_s: float
    apparent_viscosity_Pa_s: float
    shear_thinning_index: float
    model: str
    warnings: list[str] = field(default_factory=list)

    def as_dataframe(self) -> pd.DataFrame:
        """Return as a table."""
        return pd.DataFrame([self.__dict__])


def zero_shear_solution_viscosity(
    temperature_K: float,
    solids_wt: float,
    Mw: float,
    params: RheologyParameters | None = None,
) -> float:
    """Return finite positive zero-shear solution viscosity in Pa.s."""
    p = params or RheologyParameters()
    T = max(float(ensure_temperature_K(temperature_K, default_unit="K")), 1.0)
    solids = clamp(positive(solids_wt) / 100.0, 0.0, 0.75)
    mu_T = p.mu_solvent_ref_Pa_s * math.exp(clamp(p.E_mu_J_mol / R_GAS * (1.0 / T - 1.0 / p.T_ref_K), -40.0, 40.0))
    polymer_factor = math.exp(clamp(p.A_mu * solids + p.B_mu * solids**2, 0.0, 60.0))
    mw_factor = (max(float(Mw), 50000.0) / 300000.0) ** max(p.alpha_Mw, 0.0)
    return clamp(mu_T * polymer_factor * mw_factor, 1.0e-8, 1.0e4)


def apparent_viscosity_from_zero_shear(
    zero_shear_viscosity_Pa_s: float,
    shear_rate_s: float,
    model: str = "newtonian",
    params: RheologyParameters | None = None,
) -> float:
    """Return apparent viscosity for Newtonian, power-law or Carreau-Yasuda models."""
    p = params or RheologyParameters(model=model)
    kind = (model or p.model or "newtonian").lower().replace("_", "-")
    mu0 = clamp(positive(ensure_viscosity_Pa_s(zero_shear_viscosity_Pa_s, default_unit="Pa.s"), 1.0e-8), 1.0e-8, 1.0e4)
    gamma = max(positive(shear_rate_s), 1.0e-6)
    if kind in {"power-law", "power law", "powerlaw"}:
        n = clamp(p.power_law_n, 0.2, 1.2)
        consistency = mu0 * max(p.reference_shear_rate_s, 1.0e-6) ** (1.0 - n)
        return clamp(consistency * gamma ** (n - 1.0), 1.0e-8, mu0 * 50.0)
    if kind in {"carreau", "carreau-yasuda", "carreau yasuda"}:
        mu_inf = mu0 * clamp(p.carreau_mu_inf_ratio, 0.0, 0.9)
        lam = max(p.carreau_lambda_s, 1.0e-9)
        a = max(p.carreau_a, 0.2)
        n = clamp(p.carreau_n, 0.05, 1.2)
        return clamp(mu_inf + (mu0 - mu_inf) * (1.0 + (lam * gamma) ** a) ** ((n - 1.0) / a), 1.0e-8, mu0 * 50.0)
    return mu0


def calculate_rheology(
    temperature_K: float,
    solids_wt: float,
    Mw: float,
    shear_rate_s: float,
    solvent: str = "hexane",
    rheology_params: RheologyParameters | dict[str, Any] | None = None,
) -> RheologyResult:
    """Calculate dynamic and apparent viscosity with trend-safe guards."""
    params = rheology_params if isinstance(rheology_params, RheologyParameters) else RheologyParameters(**(rheology_params or {}))
    warnings: list[str] = []
    temperature_K = ensure_temperature_K(temperature_K, default_unit="K")
    if temperature_K <= 0.0:
        warnings.append("temperature_K must be positive; clipped for rheology calculation.")
    if solvent not in {"hexane", "heptane", "toluene", "custom"}:
        warnings.append(f"Unknown solvent {solvent}; using reference solvent viscosity.")
    mu0 = zero_shear_solution_viscosity(temperature_K, solids_wt, Mw, params)
    mu_app = apparent_viscosity_from_zero_shear(mu0, shear_rate_s, params.model, params)
    shear_index = clamp(mu_app / max(mu0, 1.0e-12), 0.0, 50.0)
    return RheologyResult(mu0, mu_app, shear_index, params.model, warnings)


def rheology_models_dataframe() -> pd.DataFrame:
    """Return supported rheology model names."""
    return pd.DataFrame(
        [
            {"model": "newtonian", "trend": "apparent viscosity independent of shear"},
            {"model": "power-law", "trend": "n<1 gives shear thinning"},
            {"model": "carreau-yasuda", "trend": "bounded high/low shear transition"},
            {"model": "EPDM empirical solution viscosity", "trend": "solids/Mw/T dependent zero-shear proxy"},
        ]
    )
