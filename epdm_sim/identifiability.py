"""Parameter identifiability diagnostics using finite-difference proxies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .flowsheet import ProcessConfig, load_default_config, run_flowsheet
from .parameter_estimation import ESTIMATED_PARAMETER_NAMES, default_estimation_parameters
from .utils import safe_divide


@dataclass
class IdentifiabilityResult:
    """Fisher-information proxy and parameter identifiability summary."""

    sensitivity_matrix: pd.DataFrame
    parameter_correlation: pd.DataFrame
    condition_number: float
    status: pd.DataFrame
    warnings: list[str]

    def as_dataframe(self) -> pd.DataFrame:
        """Return compact summary rows."""
        return self.status.copy()


def _proxy_prediction(params: dict[str, float], config: ProcessConfig) -> np.ndarray:
    """Return a deterministic KPI proxy sensitive to estimated parameters."""
    base = run_flowsheet(config).kpis
    c2 = float(base["C2_wt"]) * (params["k_E_ref"] / max(params["k_E_ref"] + params["k_P_ref"], 1.0)) / 0.58
    enb = float(base["ENB_wt"]) * (params["k_ENB_ref"] / max(params["k_E_ref"], 1.0)) ** 0.08 / (1.0 + 0.08 * params["beta_P"])
    mw = params["Mw0"] / (1.0 + 0.015 * params["ktr_H2"] * max(config.hydrogen_g_h, 0.0) / 5.0)
    mooney = float(base["Mooney"]) * (mw / max(float(base["Mw"]), 1.0)) ** 0.55
    activity = float(base["polymer_kg_h"]) * params["activity_decay_factor"] * np.exp(-0.1 * params["kd_h"])
    return np.array([c2, enb, mooney, mw / 10000.0, activity], dtype=float)


def finite_difference_sensitivity(
    config: ProcessConfig | None = None,
    parameter_names: list[str] | None = None,
    relative_step: float = 1.0e-3,
) -> pd.DataFrame:
    """Compute a finite-difference sensitivity matrix for key KPIs."""
    cfg = config or load_default_config()
    params = default_estimation_parameters()
    names = parameter_names or ["k_E_ref", "k_P_ref", "k_ENB_ref", "beta_P", "beta_E", "Mw0", "ktr_H2", "kd_h"]
    base = _proxy_prediction(params, cfg)
    rows: list[dict[str, float | str]] = []
    targets = ["C2_wt", "ENB_wt", "Mooney", "Mw_scaled", "activity"]
    for name in names:
        perturbed = dict(params)
        step = max(abs(params[name]) * relative_step, 1.0e-9)
        perturbed[name] = params[name] + step
        diff = (_proxy_prediction(perturbed, cfg) - base) / step
        row: dict[str, float | str] = {"parameter": name}
        row.update({target: float(value) for target, value in zip(targets, diff)})
        rows.append(row)
    return pd.DataFrame(rows)


def evaluate_identifiability(
    experiment_data: pd.DataFrame | None = None,
    config: ProcessConfig | None = None,
) -> IdentifiabilityResult:
    """Evaluate parameter identifiability from sensitivity and data coverage."""
    sensitivity = finite_difference_sensitivity(config)
    matrix = sensitivity.drop(columns=["parameter"]).to_numpy(dtype=float)
    fim = matrix @ matrix.T
    condition = float(np.linalg.cond(fim + np.eye(fim.shape[0]) * 1.0e-12))
    std = matrix.std(axis=1)
    if np.any(std < 1.0e-30):
        corr = np.eye(matrix.shape[0])
    else:
        corr = np.corrcoef(matrix)
    corr_df = pd.DataFrame(corr, index=sensitivity["parameter"], columns=sensitivity["parameter"]).replace([np.inf, -np.inf], 0.0).fillna(0.0)
    statuses: list[dict[str, Any]] = []
    warnings: list[str] = []
    weak_by_data: set[str] = set()
    if experiment_data is not None and not experiment_data.empty:
        if "pressure_MPa" not in experiment_data or experiment_data["pressure_MPa"].nunique(dropna=True) < 2:
            weak_by_data.add("beta_P")
            warnings.append("beta_P需要压力梯度数据。")
        ratio = safe_divide(float(experiment_data.get("ethylene_feed", pd.Series([0])).std()), max(float(experiment_data.get("enb_feed", pd.Series([1])).std()), 1.0e-12), 0.0)
        if ratio == 0.0:
            weak_by_data.add("beta_E")
            warnings.append("beta_E需要C_E/C_ENB梯度数据。")
        if "hydrogen_feed" not in experiment_data or experiment_data["hydrogen_feed"].nunique(dropna=True) < 2:
            weak_by_data.add("ktr_H2")
            warnings.append("ktr_H2需要H2梯度数据。")
        if "residence_time_min" not in experiment_data or experiment_data["residence_time_min"].nunique(dropna=True) < 2:
            weak_by_data.add("kd_h")
            warnings.append("kd_h需要时间/停留时间梯度数据。")
    for idx, name in enumerate(sensitivity["parameter"]):
        norm = float(np.linalg.norm(matrix[idx]))
        status = "identifiable"
        reason = "finite sensitivity"
        if norm < 1.0e-10:
            status = "not_identifiable"
            reason = "near-zero sensitivity"
        elif name in weak_by_data or condition > 1.0e12:
            status = "weakly_identifiable"
            reason = "limited data variation or high condition number"
        statuses.append({"parameter": name, "sensitivity_norm": norm, "status": status, "reason": reason})
    return IdentifiabilityResult(sensitivity, corr_df, condition, pd.DataFrame(statuses), warnings)
