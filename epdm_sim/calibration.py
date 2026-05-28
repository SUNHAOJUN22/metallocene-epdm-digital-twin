"""Experiment-data calibration and DOE utilities for the EPDM digital twin."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import numpy as np
import pandas as pd

from .flowsheet import ProcessConfig
from .kinetics import KineticParameters
from .polymer_props import estimate_mooney, load_internal_experiments
from .utils import clamp, data_path, load_json, model_dump_compat, positive, safe_divide


@lru_cache(maxsize=1)
def load_catalysts() -> dict[str, dict[str, Any]]:
    """Load catalyst knowledge records extracted from project and PDF rules."""
    return load_json(data_path("catalysts.json"))


def catalyst_dataframe() -> pd.DataFrame:
    """Return catalyst knowledge records as a flat DataFrame for UI display."""
    rows: list[dict[str, Any]] = []
    for catalyst_id, record in load_catalysts().items():
        row = dict(record)
        row["catalyst_id"] = catalyst_id
        row["pressure_window_MPa"] = " - ".join(str(v) for v in row.get("pressure_window_MPa", []))
        row["AlTi_window"] = " - ".join(str(v) for v in row.get("AlTi_window", []))
        row["notes"] = "; ".join(row.get("notes", []))
        rows.append(row)
    return pd.DataFrame(rows)


def pdf_rules_dataframe() -> pd.DataFrame:
    """Return the research-summary rules as a two-column table."""
    rules = load_catalysts().get("PDF_rules", {}).get("notes", [])
    return pd.DataFrame({"rule": list(range(1, len(rules) + 1)), "research_summary_rule": rules})


@dataclass
class CalibrationResult:
    """Calibration output for kinetics, product properties and diagnostics."""

    params: dict[str, float]
    residuals: pd.DataFrame
    r2: dict[str, float]
    mae: dict[str, float]
    warnings: list[str] = field(default_factory=list)
    plots_data: dict[str, pd.DataFrame] = field(default_factory=dict)

    def params_dataframe(self) -> pd.DataFrame:
        """Return fitted parameters as a DataFrame."""
        return pd.DataFrame([{"parameter": key, "value": value} for key, value in self.params.items()])

    def metrics_dataframe(self) -> pd.DataFrame:
        """Return R2 and MAE calibration metrics as a DataFrame."""
        metrics = sorted(set(self.r2) | set(self.mae))
        return pd.DataFrame(
            [{"target": target, "r2": self.r2.get(target, np.nan), "mae": self.mae.get(target, np.nan)} for target in metrics]
        )


def _ep_ratio_to_fraction(value: Any) -> float:
    """Convert an E/P ratio string such as 1:2 to an ethylene feed fraction."""
    try:
        left, right = str(value).split(":", maxsplit=1)
        e = positive(float(left), 0.0)
        p = positive(float(right), 0.0)
        return safe_divide(e, e + p, 0.5)
    except Exception:
        return 0.5


def _prepared_experiments() -> pd.DataFrame:
    """Load experiments and add robust engineered features."""
    df = load_internal_experiments().copy()
    df["E_feed_fraction"] = df["ep_ratio"].map(_ep_ratio_to_fraction)
    df["ENB_feed_ml"] = pd.to_numeric(df.get("enb_ml", 0.0), errors="coerce").fillna(0.0)
    df["activity_g_mol_h"] = pd.to_numeric(df.get("activity_1e7_g_mol_h", 0.0), errors="coerce").fillna(0.0) * 1.0e7
    for col in ["C2_wt", "C3_wt", "ENB_wt", "Mw", "PDI", "mooney", "polymer_g"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _fit_linear(df: pd.DataFrame, target: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Fit a small regularized linear model for a target and return y/yhat/coefs."""
    clean = df.dropna(subset=[target, "E_feed_fraction", "ENB_feed_ml", "activity_g_mol_h"])
    if len(clean) < 4:
        raise ValueError(f"Not enough data to fit {target}")
    X = np.column_stack(
        [
            np.ones(len(clean)),
            clean["E_feed_fraction"].to_numpy(dtype=float),
            clean["ENB_feed_ml"].to_numpy(dtype=float),
            np.log1p(clean["activity_g_mol_h"].to_numpy(dtype=float) / 1.0e7),
        ]
    )
    y = clean[target].to_numpy(dtype=float)
    if target in {"Mw", "mooney", "activity_g_mol_h"}:
        y_fit = np.log(np.maximum(y, 1.0))
    else:
        y_fit = y
    ridge = np.eye(X.shape[1]) * 1.0e-8
    ridge[0, 0] = 0.0
    coeffs = np.linalg.solve(X.T @ X + ridge, X.T @ y_fit)
    pred_fit = X @ coeffs
    pred = np.exp(pred_fit) if target in {"Mw", "mooney", "activity_g_mol_h"} else pred_fit
    return y, pred, coeffs


def _r2_mae(y: np.ndarray, pred: np.ndarray) -> tuple[float, float]:
    """Return R2 and MAE with stable fallback for tiny variance."""
    y = np.asarray(y, dtype=float)
    pred = np.asarray(pred, dtype=float)
    ss_res = float(np.sum((y - pred) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - safe_divide(ss_res, ss_tot, 0.0) if ss_tot > 1.0e-12 else 1.0
    mae = float(np.mean(np.abs(y - pred))) if y.size else 0.0
    return float(clamp(r2, -5.0, 1.0)), mae


@lru_cache(maxsize=4)
def calibrate_from_internal_data(target_focus: str = "ENB wt%") -> CalibrationResult:
    """Calibrate apparent parameters and empirical prediction residuals.

    This is intentionally conservative: it fits small empirical response
    surfaces from the available internal experiments and maps stable trends
    into the existing apparent kinetic parameters. When the data are not
    enough for a parameter, the default kinetic value is kept and a warning is
    returned.
    """
    df = _prepared_experiments()
    defaults = KineticParameters()
    warnings: list[str] = []
    residual_frames: list[pd.DataFrame] = []
    r2: dict[str, float] = {}
    mae: dict[str, float] = {}
    coeffs_by_target: dict[str, np.ndarray] = {}
    target_map = {
        "C2_wt": "C2 wt%",
        "ENB_wt": "ENB wt%",
        "Mw": "Mw",
        "mooney": "Mooney",
        "activity_g_mol_h": "activity",
    }
    for target, label in target_map.items():
        try:
            y, pred, coeffs = _fit_linear(df, target)
            coeffs_by_target[target] = coeffs
            metric_r2, metric_mae = _r2_mae(y, pred)
            r2[label] = metric_r2
            mae[label] = metric_mae
            clean = df.dropna(subset=[target]).copy().head(len(y))
            residual_frames.append(
                pd.DataFrame(
                    {
                        "target": label,
                        "run_id": clean["run_id"].to_numpy(),
                        "observed": y,
                        "predicted": pred,
                        "residual": y - pred,
                    }
                )
            )
        except Exception as exc:
            warnings.append(f"{label} 校准使用默认趋势：{exc}")
    residuals = pd.concat(residual_frames, ignore_index=True) if residual_frames else pd.DataFrame()

    enb_slope = float(coeffs_by_target.get("ENB_wt", np.array([0.0, 0.0, 1.25, 0.0]))[2])
    c2_feed_slope = float(coeffs_by_target.get("C2_wt", np.array([0.0, 42.0, 0.0, 0.0]))[1])
    c2_enb_slope = float(coeffs_by_target.get("C2_wt", np.array([0.0, 0.0, -1.0, 0.0]))[2])
    median_mw = float(df["Mw"].dropna().median()) if df["Mw"].notna().any() else defaults.Mw0
    median_activity = float(df["activity_g_mol_h"].dropna().median()) if df["activity_g_mol_h"].notna().any() else 8.0e7
    params = {
        "k_E_ref": defaults.k_E_ref * clamp(abs(c2_feed_slope) / 42.0, 0.55, 1.75),
        "k_P_ref": defaults.k_P_ref * clamp((100.0 - df["C2_wt"].mean()) / 45.0, 0.55, 1.65),
        "k_ENB_ref": defaults.k_ENB_ref * clamp(max(enb_slope, 0.2) / 1.25, 0.45, 2.4),
        "beta_P": 0.55,
        "beta_E": clamp(abs(c2_enb_slope) / 100.0, 0.005, 0.08),
        "Mw0": clamp(median_mw * 1.45, 250000.0, 1200000.0),
        "ktr_H2": defaults.ktr_H2,
        "kd_h": defaults.kd_h * clamp(8.0e7 / max(median_activity, 1.0), 0.45, 1.8),
    }
    if "hydrogen_g_h" not in df.columns or df.get("hydrogen_g_h", pd.Series(dtype=float)).nunique(dropna=True) < 2:
        warnings.append("内部数据缺少系统氢调变量，ktr_H2 保持默认值；建议优先开展氢调DOE。")
    plots_data = {
        "residuals": residuals,
        "experiments": df,
        "rules": pdf_rules_dataframe(),
    }
    return CalibrationResult(params=params, residuals=residuals, r2=r2, mae=mae, warnings=warnings, plots_data=plots_data)


def recommend_doe(target: str, base: ProcessConfig | None = None, n: int = 8) -> pd.DataFrame:
    """Recommend a compact next-experiment DOE matrix based on PDF rules."""
    cfg = base or ProcessConfig()
    target_key = target.lower()
    pressure_levels = [0.7, max(min(cfg.pressure_MPa, 1.2), 0.9), 2.0]
    enb_levels = [max(cfg.enb_kg_h * factor, 0.1) for factor in [0.65, 1.0, 1.45]]
    ep_levels = [0.5, safe_divide(cfg.ethylene_kg_h, max(cfg.propylene_kg_h, 1.0e-9), 1.0), 2.0]
    rows: list[dict[str, Any]] = []
    for i in range(max(n, 1)):
        pressure = pressure_levels[i % len(pressure_levels)]
        enb = enb_levels[(i // 2) % len(enb_levels)]
        ep_ratio = ep_levels[(i // 3) % len(ep_levels)]
        row = {
            "run": i + 1,
            "temperature_C": cfg.temperature_C + [-10, 0, 10][i % 3],
            "pressure_MPa": pressure,
            "ENB_kg_h": enb,
            "E_P_molar_ratio": ep_ratio,
            "AlTi_ratio": [500, 800, 1000][i % 3],
            "BHT_ratio": [0.0, 0.3, 0.8][i % 3],
            "H2_g_h": cfg.hydrogen_g_h if "mw" not in target_key and "mooney" not in target_key else cfg.hydrogen_g_h * [0.4, 1.0, 2.0][i % 3],
            "rpm": [350, 500, 700][i % 3],
        }
        if "enb" in target_key:
            row["rationale"] = "验证0.7MPa低压和ENB加入量对ENB引入/转化率的线性与衰减规律。"
        elif "activity" in target_key:
            row["rationale"] = "扫描Al/Ti与BHT，验证MAO降低和BHT增Mw/保活性窗口。"
        elif "mw" in target_key or "mooney" in target_key:
            row["rationale"] = "补齐氢调数据，建立H2-Mw-Mooney对应关系。"
        else:
            row["rationale"] = "用E/P、压力、ENB三因素补强组成和挂胶趋势边界。"
        rows.append(row)
    return pd.DataFrame(rows)


def hydrogen_tuning_recommendation(
    target_Mw: float,
    target_mooney: float,
    base: ProcessConfig,
    current_kpis: dict[str, Any],
) -> dict[str, Any]:
    """Recommend hydrogen feed adjustment for target Mw/Mooney."""
    current_Mw = positive(current_kpis.get("Mw", 360000.0), 360000.0)
    current_ML = positive(current_kpis.get("Mooney", 80.0), 80.0)
    base_h2 = positive(base.hydrogen_g_h)
    desired_ratio = clamp(current_Mw / max(target_Mw, 50000.0), 0.25, 5.0)
    h2_from_mw = base_h2 * max(desired_ratio, 0.05)
    if target_mooney > 0:
        mooney_ratio = clamp(current_ML / max(target_mooney, 2.0), 0.25, 4.0)
        h2_from_mooney = base_h2 * max(mooney_ratio, 0.05)
    else:
        h2_from_mooney = h2_from_mw
    recommended_h2 = 0.55 * h2_from_mw + 0.45 * h2_from_mooney
    warning = "需要氢调实测数据校准；当前建议基于Mw= Mw0/(1+ktr*C_H2) 的表观趋势。"
    if recommended_h2 > base_h2 * 2.5:
        warning += " 推荐氢气显著升高，需关注活性、低门尼和安全联锁。"
    elif recommended_h2 < base_h2 * 0.5:
        warning += " 推荐氢气降低，需关注Mw/门尼升高导致挂胶和输送风险。"
    return {
        "current_H2_g_h": base_h2,
        "recommended_H2_g_h": float(max(recommended_h2, 0.0)),
        "target_Mw": float(target_Mw),
        "current_Mw": float(current_Mw),
        "target_Mooney": float(target_mooney),
        "current_Mooney": float(current_ML),
        "warning": warning,
    }
