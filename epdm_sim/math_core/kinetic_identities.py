"""Kinetic identity helpers for V6.0 release gates."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .thermodynamic_identities import R_J_MOL_K

K_B_J_K = 1.380649e-23
H_J_S = 6.62607015e-34


def arrhenius_rate_ratio(Ea_J_mol: float, temperature_high_K: float, temperature_low_K: float) -> float:
    """Return k_high/k_low for the same pre-exponential factor."""
    high = float(temperature_high_K)
    low = float(temperature_low_K)
    if high <= 0.0 or low <= 0.0:
        raise ValueError("temperatures must be positive")
    return float(math.exp(-float(Ea_J_mol) / R_J_MOL_K * (1.0 / high - 1.0 / low)))


def eyring_rate_constant(delta_g_activation_J_mol: float, temperature_K: float) -> float:
    """Return k = kB T / h * exp(-deltaG^‡ / RT)."""
    T = float(temperature_K)
    if T <= 0.0:
        raise ValueError("temperature_K must be positive")
    exponent = -float(delta_g_activation_J_mol) / (R_J_MOL_K * T)
    return float((K_B_J_K * T / H_J_S) * math.exp(max(min(exponent, 700.0), -700.0)))


def kinetic_identity_checks_dataframe() -> pd.DataFrame:
    """Return finite/trend checks for Arrhenius and Eyring identities."""
    ratio = arrhenius_rate_ratio(45_000.0, 390.0, 350.0)
    k_eyring = eyring_rate_constant(75_000.0, 373.15)
    return pd.DataFrame(
        [
            {"identity": "Arrhenius temperature trend", "value": ratio, "unit": "-", "passed": bool(np.isfinite(ratio) and ratio > 1.0)},
            {"identity": "Eyring finite positive k", "value": k_eyring, "unit": "1/s", "passed": bool(np.isfinite(k_eyring) and k_eyring > 0.0)},
        ]
    )
