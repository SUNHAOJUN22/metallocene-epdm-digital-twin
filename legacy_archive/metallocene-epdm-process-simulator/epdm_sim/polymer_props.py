"""Empirical polymer property models and grade matching."""

from __future__ import annotations

import math
from functools import lru_cache
from typing import Any

import numpy as np
import pandas as pd

from .utils import TINY, clamp, data_path, load_json, positive, safe_divide

DEFAULT_MOONEY_COEFFS = {
    "a0": 2.765,
    "a1": 0.80,
    "a2": 0.08,
    "a3": 0.30,
    "a4": 0.80,
    "a5": 0.20,
}


@lru_cache(maxsize=1)
def load_internal_experiments() -> pd.DataFrame:
    """Load internal experiment data used for calibration."""
    return pd.read_csv(data_path("internal_experiments.csv"))


@lru_cache(maxsize=1)
def load_target_grades() -> dict[str, dict[str, Any]]:
    """Load target grade definitions."""
    return load_json(data_path("target_grades.json"))


@lru_cache(maxsize=1)
def calibrate_mooney_coefficients() -> dict[str, float]:
    """Fit Mooney model coefficients from internal experiments.

    Falls back to DEFAULT_MOONEY_COEFFS when the regression is underdetermined
    or numerically unstable.
    """
    try:
        df = load_internal_experiments().dropna(subset=["mooney", "Mw", "PDI", "C2_wt", "ENB_wt"])
        df = df[(df["mooney"] > 0) & (df["Mw"] > 0)]
        if len(df) < 6:
            return DEFAULT_MOONEY_COEFFS.copy()
        X = np.column_stack(
            [
                np.ones(len(df)),
                np.log(df["Mw"].to_numpy(dtype=float) / 100000.0),
                df["PDI"].to_numpy(dtype=float),
                df["C2_wt"].to_numpy(dtype=float) / 100.0,
                df["ENB_wt"].to_numpy(dtype=float) / 100.0,
                np.zeros(len(df)),
            ]
        )
        y = np.log(df["mooney"].to_numpy(dtype=float))
        coeffs, *_ = np.linalg.lstsq(X, y, rcond=None)
        if not np.all(np.isfinite(coeffs)):
            return DEFAULT_MOONEY_COEFFS.copy()
        keys = ["a0", "a1", "a2", "a3", "a4", "a5"]
        fitted = {key: float(value) for key, value in zip(keys, coeffs)}
        if abs(fitted["a0"]) > 5.0 or abs(fitted["a3"]) > 3.0 or abs(fitted["a4"]) > 6.0:
            return DEFAULT_MOONEY_COEFFS.copy()
        fitted["a1"] = clamp(fitted["a1"], 0.1, 2.5)
        fitted["a2"] = clamp(fitted["a2"], -0.8, 1.2)
        fitted["a3"] = clamp(fitted["a3"], -2.0, 2.0)
        fitted["a4"] = clamp(fitted["a4"], -3.0, 4.0)
        return fitted
    except Exception:
        return DEFAULT_MOONEY_COEFFS.copy()


@lru_cache(maxsize=1)
def calibrate_enb_feed_relationship() -> dict[str, float]:
    """Fit a simple ENB feed-to-product empirical relationship."""
    try:
        df = load_internal_experiments().dropna(subset=["enb_ml", "ENB_wt"])
        X = np.column_stack([np.ones(len(df)), df["enb_ml"].to_numpy(dtype=float)])
        y = df["ENB_wt"].to_numpy(dtype=float)
        coeffs, *_ = np.linalg.lstsq(X, y, rcond=None)
        return {"intercept": float(coeffs[0]), "slope": float(coeffs[1])}
    except Exception:
        return {"intercept": 0.3, "slope": 1.3}


def estimate_mooney(
    Mw: float,
    PDI: float,
    C2_wt: float,
    ENB_wt: float,
    LCB_index: float = 0.0,
    coeffs: dict[str, float] | None = None,
) -> float:
    """Estimate Mooney viscosity ML(1+4) from empirical logarithmic model."""
    c = coeffs or calibrate_mooney_coefficients()
    ln_ml = (
        c["a0"]
        + c["a1"] * math.log(max(Mw, 1000.0) / 100000.0)
        + c["a2"] * PDI
        + c["a3"] * (C2_wt / 100.0)
        + c["a4"] * (ENB_wt / 100.0)
        + c["a5"] * positive(LCB_index)
    )
    return clamp(math.exp(clamp(ln_ml, 1.0, 6.5)), 2.0, 700.0)


def estimate_tg(C2_wt: float, C3_wt: float, ENB_wt: float) -> float:
    """Estimate glass transition temperature by a Fox equation in Celsius."""
    weights = {
        "E": positive(C2_wt) / 100.0,
        "P": positive(C3_wt) / 100.0,
        "D": positive(ENB_wt) / 100.0,
    }
    total = sum(weights.values())
    if total <= TINY:
        return -50.0
    weights = {key: value / total for key, value in weights.items()}
    tg_K = safe_divide(
        1.0,
        weights["E"] / 200.0 + weights["P"] / 260.0 + weights["D"] / 300.0,
        223.15,
    )
    return tg_K - 273.15 + 0.25 * ENB_wt


def estimate_tm_and_crystallinity(C2_wt: float, C3_wt: float) -> tuple[float | None, str]:
    """Estimate melting peak and crystallization risk from ethylene content."""
    if C2_wt < 55.0:
        return None, "no melting peak"
    propylene_noise = max(C3_wt - 25.0, 0.0)
    tm_est = 40.0 + 1.5 * (C2_wt - 50.0) - 0.8 * propylene_noise
    if C2_wt > 65.0 and C3_wt < 35.0:
        return tm_est, "crystallization risk"
    return tm_est, "weak melting peak"


def fouling_risk_index(
    solids_wt: float,
    Mw: float,
    PDI: float,
    ethylene_wt: float,
    temperature_K: float,
    mooney: float,
) -> tuple[float, str]:
    """Estimate normalized fouling and transfer risk."""
    normalized_viscosity = (
        (positive(solids_wt) / 20.0) ** 2
        * (max(Mw, 50000.0) / 300000.0) ** 0.8
        * math.exp(1500.0 / max(temperature_K, 250.0))
        / 55.0
    )
    comp_factor = 1.0 + 0.012 * max(ethylene_wt - 55.0, 0.0)
    pdi_factor = 1.0 + 0.10 * max(PDI - 3.0, 0.0)
    mooney_factor = 1.0 + 0.006 * max(mooney - 80.0, 0.0)
    index = normalized_viscosity * comp_factor * pdi_factor * mooney_factor
    if index < 1.0:
        level = "low"
    elif index < 3.0:
        level = "medium"
    else:
        level = "high"
    return float(index), level


def grade_match(product: dict[str, float], grade_id: str) -> dict[str, Any]:
    """Score current product against a target grade definition."""
    grades = load_target_grades()
    grade = grades[grade_id]
    metrics = {
        "C2": (product.get("C2_wt", product.get("ethylene_wt", 0.0)), grade["C2_min"], grade["C2_max"]),
        "ENB": (product.get("ENB_wt", 0.0), grade["ENB_min"], grade["ENB_max"]),
        "ML": (product.get("Mooney", product.get("mooney", 0.0)), grade["ML_min"], grade["ML_max"]),
    }
    penalties = {}
    total_penalty = 0.0
    for key, (value, low, high) in metrics.items():
        span = max(high - low, 1.0)
        if low <= value <= high:
            penalty = 0.0
        elif value < low:
            penalty = (low - value) / span
        else:
            penalty = (value - high) / span
        penalties[key] = penalty
        total_penalty += penalty
    score = clamp(100.0 * math.exp(-0.8 * total_penalty), 0.0, 100.0)
    return {"grade_id": grade_id, "grade": grade, "score": score, "penalties": penalties}


def generate_recommendations(result: dict[str, Any]) -> list[str]:
    """Generate engineering recommendations from simulation KPIs."""
    recs: list[str] = []
    C2 = result.get("C2_wt", 0.0)
    ENB = result.get("ENB_wt", 0.0)
    mooney = result.get("Mooney", 0.0)
    residue = result.get("ENB_residue_ppm", 0.0)
    fouling = result.get("fouling_index", 0.0)
    if ENB < 5.0:
        recs.append("产品 ENB 偏低：优先降低反应压力至 0.7 MPa 附近或提高 ENB 进料。")
    elif ENB > 10.0:
        recs.append("产品 ENB 偏高：可降低 ENB 进料或适当提高乙烯/ENB竞争比例。")
    if C2 > 68.0:
        recs.append("乙烯含量偏高且可能带来结晶风险：降低 E/P 比或提高丙烯进料。")
    if mooney > 120.0:
        recs.append("门尼较高：提高氢气用量或降低停留时间以降低 Mw。")
    elif 0.0 < mooney < 45.0:
        recs.append("门尼较低：降低氢气、提高催化活性或延长停留时间。")
    if residue > 50000.0:
        recs.append("ENB 残留较高：提高二级闪蒸温度、降低压力或增加脱挥停留。")
    if fouling >= 3.0:
        recs.append("挂胶风险高：降低固含、降低 Mw/门尼或提高输送温度并加强换热器清洗策略。")
    if not recs:
        recs.append("当前工况处于较稳定窗口，可围绕 ENB 和氢气做小步敏感性验证。")
    return recs
