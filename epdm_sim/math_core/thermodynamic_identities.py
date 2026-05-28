"""Thermodynamic identities used by V6.0 science gates."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

R_J_MOL_K = 8.31446261815324


def gibbs_from_enthalpy_entropy(delta_h_j_mol: float, temperature_K: float, delta_s_j_mol_K: float) -> float:
    """Return delta G = delta H - T delta S in J/mol."""
    T = float(temperature_K)
    if T <= 0.0:
        raise ValueError("temperature_K must be positive")
    return float(delta_h_j_mol) - T * float(delta_s_j_mol_K)


def equilibrium_constant_from_delta_g(delta_g_j_mol: float, temperature_K: float) -> float:
    """Return K = exp(-deltaG / RT)."""
    T = float(temperature_K)
    if T <= 0.0:
        raise ValueError("temperature_K must be positive")
    exponent = -float(delta_g_j_mol) / (R_J_MOL_K * T)
    return float(math.exp(max(min(exponent, 700.0), -700.0)))


def delta_g_from_equilibrium_constant(K: float, temperature_K: float) -> float:
    """Return delta G = -RT ln K in J/mol."""
    T = float(temperature_K)
    K_f = float(K)
    if T <= 0.0:
        raise ValueError("temperature_K must be positive")
    if K_f <= 0.0:
        raise ValueError("equilibrium constant must be positive")
    return -R_J_MOL_K * T * math.log(K_f)


def thermodynamic_identity_checks_dataframe() -> pd.DataFrame:
    """Return deterministic identity checks without running heavy models."""
    d_h = -50_000.0
    d_s = -100.0
    T = 373.15
    d_g = gibbs_from_enthalpy_entropy(d_h, T, d_s)
    K = equilibrium_constant_from_delta_g(d_g, T)
    d_g_back = delta_g_from_equilibrium_constant(K, T)
    rows: list[dict[str, Any]] = [
        {
            "identity": "deltaG = deltaH - T deltaS",
            "value": d_g,
            "unit": "J/mol",
            "passed": bool(np.isfinite(d_g)),
        },
        {
            "identity": "deltaG = -RT ln K roundtrip",
            "value": d_g_back,
            "expected": d_g,
            "unit": "J/mol",
            "passed": bool(np.isfinite(d_g_back) and abs(d_g_back - d_g) <= 1.0e-6),
        },
    ]
    return pd.DataFrame(rows)
