"""Nonlinear parameter estimation and parameter-set version management."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import differential_evolution, least_squares

from .experiment_data import calibration_subset, load_internal_experiment_dataset, normalize_experiments
from .kinetics import KineticParameters
from .polymer_props import estimate_mooney
from .utils import clamp, data_path, load_json, model_dump_compat, safe_divide, write_json


ESTIMATED_PARAMETER_NAMES = [
    "k_E_ref",
    "k_P_ref",
    "k_ENB_ref",
    "beta_P",
    "beta_E",
    "Mw0",
    "ktr_H2",
    "kd_h",
    "pressure_optimum_MPa",
    "enb_feed_slope",
    "activity_decay_factor",
]

DEFAULT_BOUNDS = {
    "k_E_ref": (5.0e5, 1.5e7),
    "k_P_ref": (2.0e5, 1.0e7),
    "k_ENB_ref": (3.0e5, 1.8e7),
    "beta_P": (0.01, 2.5),
    "beta_E": (0.0001, 0.20),
    "Mw0": (120000.0, 1800000.0),
    "ktr_H2": (1.0, 250.0),
    "kd_h": (0.005, 0.80),
    "pressure_optimum_MPa": (0.4, 1.2),
    "enb_feed_slope": (0.20, 3.0),
    "activity_decay_factor": (0.20, 3.0),
}

TARGET_COLUMNS = {
    "C2_wt": "C2_wt",
    "C3_wt": "C3_wt",
    "ENB_wt": "ENB_wt",
    "Mooney": "Mooney",
    "Mw": "Mw",
    "PDI": "PDI",
    "activity": "activity",
    "polymer_g": "polymer_g",
    "conversion_E": "conversion_E",
    "conversion_P": "conversion_P",
    "conversion_ENB": "conversion_ENB",
    "dynamic_T_profile": "dynamic_T_profile",
    "dynamic_Q_profile": "dynamic_Q_profile",
}

MODEL_MODES = {"empirical_proxy", "flowsheet_real", "dynamic_ode_real", "hybrid"}


@dataclass
class ParameterEstimationResult:
    """Output from nonlinear parameter estimation."""

    target: str
    method: str
    fitted_params: dict[str, float]
    default_params: dict[str, float]
    residuals: pd.DataFrame
    r2: dict[str, float]
    mae: dict[str, float]
    train_test_metrics: pd.DataFrame
    confidence: pd.DataFrame
    confidence_interval: pd.DataFrame = field(default_factory=pd.DataFrame)
    parameter_correlation: pd.DataFrame = field(default_factory=pd.DataFrame)
    dataset_id: str = "internal_experiments"
    warnings: list[str] = field(default_factory=list)
    run_failures: pd.DataFrame = field(default_factory=pd.DataFrame)
    fitting_runtime_s: float = 0.0
    model_mode: str = "empirical_proxy"

    def params_dataframe(self) -> pd.DataFrame:
        """Return fitted and default parameter values."""
        rows = []
        for name in ESTIMATED_PARAMETER_NAMES:
            rows.append(
                {
                    "parameter": name,
                    "default": self.default_params.get(name),
                    "fitted": self.fitted_params.get(name),
                    "relative_change_pct": 100.0
                    * safe_divide(self.fitted_params.get(name, 0.0) - self.default_params.get(name, 0.0), max(abs(self.default_params.get(name, 0.0)), 1.0e-12), 0.0),
                }
            )
        return pd.DataFrame(rows)

    def metrics_dataframe(self) -> pd.DataFrame:
        """Return target metrics."""
        return pd.DataFrame(
            [
                {
                    "target": target,
                    "r2": self.r2.get(target, np.nan),
                    "mae": self.mae.get(target, np.nan),
                }
                for target in self.r2
            ]
        )

    def confidence_dataframe(self) -> pd.DataFrame:
        """Return parameter confidence proxy."""
        return self.confidence.copy()


def default_estimation_parameters() -> dict[str, float]:
    """Return the default estimation parameter dictionary."""
    kin = model_dump_compat(KineticParameters())
    defaults = {name: float(kin[name]) for name in ["k_E_ref", "k_P_ref", "k_ENB_ref", "beta_P", "beta_E", "Mw0", "ktr_H2", "kd_h"]}
    defaults.update({"pressure_optimum_MPa": 0.7, "enb_feed_slope": 1.0, "activity_decay_factor": 1.0})
    return defaults


def load_parameter_sets(path: str | Path | None = None) -> dict[str, Any]:
    """Load parameter-set registry."""
    registry_path = Path(path or data_path("parameter_sets.json"))
    if not registry_path.exists():
        payload = {"active_set_id": "default", "sets": {}}
        write_json(registry_path, payload)
        return payload
    payload = load_json(registry_path)
    payload.setdefault("active_set_id", "default")
    payload.setdefault("sets", {})
    return payload


def parameter_sets_dataframe(path: str | Path | None = None) -> pd.DataFrame:
    """Return parameter sets as a compact table."""
    registry = load_parameter_sets(path)
    rows = []
    for set_id, item in registry.get("sets", {}).items():
        params = item.get("parameters", {})
        rows.append(
            {
                "set_id": set_id,
                "active": set_id == registry.get("active_set_id"),
                "source": item.get("source", ""),
                "catalyst_id": item.get("catalyst_id", ""),
                "description": item.get("description", ""),
                "k_E_ref": params.get("k_E_ref"),
                "k_P_ref": params.get("k_P_ref"),
                "k_ENB_ref": params.get("k_ENB_ref"),
                "beta_P": params.get("beta_P"),
                "Mw0": params.get("Mw0"),
            }
        )
    return pd.DataFrame(rows)


def save_parameter_set(
    set_id: str,
    parameters: dict[str, float],
    *,
    description: str = "",
    source: str = "user-calibrated",
    catalyst_id: str = "unknown",
    metrics: dict[str, Any] | None = None,
    path: str | Path | None = None,
    make_active: bool = True,
    dataset_id: str = "internal_experiments",
    fit_method: str = "",
    fitted_targets: list[str] | None = None,
    confidence_interval: pd.DataFrame | dict[str, Any] | None = None,
    model_mode: str | None = None,
    fitting_runtime_s: float | None = None,
    run_failures: pd.DataFrame | list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Save a parameter set without overwriting built-in defaults unless explicitly requested."""
    registry_path = Path(path or data_path("parameter_sets.json"))
    registry = load_parameter_sets(registry_path)
    clean_id = str(set_id).strip() or "user_calibrated"
    registry["sets"][clean_id] = {
        "set_id": clean_id,
        "description": description or "User-calibrated apparent kinetic parameter set.",
        "source": source,
        "catalyst_id": catalyst_id,
        "parameters": {name: float(parameters[name]) for name in ESTIMATED_PARAMETER_NAMES if name in parameters},
        "metrics": metrics or {},
        "dataset_id": dataset_id,
        "fit_method": fit_method,
        "model_mode": model_mode or fit_method or "",
        "fitted_targets": fitted_targets or [],
        "confidence_interval": confidence_interval.to_dict(orient="records") if hasattr(confidence_interval, "to_dict") else (confidence_interval or {}),
        "fitting_runtime_s": float(fitting_runtime_s or 0.0),
        "run_failures": run_failures.to_dict(orient="records") if hasattr(run_failures, "to_dict") else (run_failures or []),
        "created_at": pd.Timestamp.now(tz="UTC").isoformat(),
        "created_by": "user",
    }
    if make_active:
        registry["active_set_id"] = clean_id
    write_json(registry_path, registry)
    return registry


def set_active_parameter_set(set_id: str, path: str | Path | None = None) -> dict[str, Any]:
    """Set the active parameter set in the registry."""
    registry_path = Path(path or data_path("parameter_sets.json"))
    registry = load_parameter_sets(registry_path)
    if set_id not in registry.get("sets", {}):
        raise KeyError(f"Unknown parameter set: {set_id}")
    registry["active_set_id"] = set_id
    write_json(registry_path, registry)
    return registry


def get_parameter_set_parameters(set_id: str | None = None, path: str | Path | None = None) -> dict[str, float]:
    """Return a full parameter dictionary for a set id, falling back to defaults."""
    registry = load_parameter_sets(path)
    selected = set_id or registry.get("active_set_id") or "default"
    item = registry.get("sets", {}).get(selected) or registry.get("sets", {}).get("default", {})
    params = default_estimation_parameters()
    params.update({key: float(value) for key, value in item.get("parameters", {}).items() if key in ESTIMATED_PARAMETER_NAMES})
    return params


def kinetic_parameters_from_set(set_id: str | None = None) -> KineticParameters:
    """Build KineticParameters from a stored parameter set."""
    params = get_parameter_set_parameters(set_id)
    kinetic_fields = set(model_dump_compat(KineticParameters()).keys())
    return KineticParameters(**{key: value for key, value in params.items() if key in kinetic_fields})


def estimate_parameters(
    experiments: pd.DataFrame | None = None,
    target: str = "combined",
    *,
    method: str = "least_squares",
    fixed_params: dict[str, float] | None = None,
    weights: dict[str, float] | None = None,
    max_nfev: int = 120,
    fit_against_flowsheet: bool = False,
    fit_against_dynamic: bool = False,
    dataset_id: str = "internal_experiments",
    model_mode: str = "empirical_proxy",
    max_seconds: float | None = None,
    early_stop: bool = True,
    failed_run_penalty: float = 8.0,
    cache_by_parameter_hash: bool = True,
) -> ParameterEstimationResult:
    """Estimate apparent model parameters from normalized experimental data."""
    started_at = time.perf_counter()
    if model_mode == "empirical_proxy":
        if fit_against_dynamic:
            model_mode = "dynamic_ode_real"
        elif fit_against_flowsheet:
            model_mode = "flowsheet_real"
    if model_mode not in MODEL_MODES:
        model_mode = "empirical_proxy"
    raw = experiments if experiments is not None else load_internal_experiment_dataset()
    df = calibration_subset(normalize_experiments(raw))
    warnings: list[str] = []
    if len(df) < 4:
        warnings.append("可用于校准的数据点少于4个，参数可信度有限。")
    if df["hydrogen_feed"].fillna(0.0).nunique() < 2:
        warnings.append("缺少系统氢调变量，ktr_H2主要由默认值和弱约束决定。")
    default_params = default_estimation_parameters()
    fixed_params = fixed_params or {}
    weights = weights or {"C2_wt": 1.0, "ENB_wt": 1.4, "Mooney": 0.25, "Mw": 1.0e-5, "activity": 0.35}
    free_names = [name for name in ESTIMATED_PARAMETER_NAMES if name not in fixed_params]
    bounds = np.array([DEFAULT_BOUNDS[name] for name in free_names], dtype=float)
    x0 = np.array([default_params[name] for name in free_names], dtype=float)
    x0 = np.clip(x0, bounds[:, 0], bounds[:, 1])
    selected_targets = list(TARGET_COLUMNS) if target == "combined" else [TARGET_COLUMNS.get(target, target)]
    selected_targets = [name for name in selected_targets if name in TARGET_COLUMNS]
    if not selected_targets:
        selected_targets = list(TARGET_COLUMNS)

    prediction_cache: dict[tuple[float, ...], pd.DataFrame] = {}
    last_failures: list[dict[str, Any]] = []

    def unpack(x: np.ndarray) -> dict[str, float]:
        params = default_params.copy()
        params.update(fixed_params)
        params.update({name: float(value) for name, value in zip(free_names, x)})
        return params

    def objective_vector(x: np.ndarray) -> np.ndarray:
        if max_seconds is not None and time.perf_counter() - started_at > max_seconds:
            if early_stop:
                return np.full(len(selected_targets) + 1, failed_run_penalty, dtype=float)
        params = unpack(x)
        cache_key = tuple(round(float(params[name]), 8) for name in ESTIMATED_PARAMETER_NAMES)
        if cache_by_parameter_hash and cache_key in prediction_cache:
            predictions = prediction_cache[cache_key]
        else:
            predictions = _predict_experiment_table(df, params, model_mode=model_mode, failed_run_penalty=failed_run_penalty)
            if cache_by_parameter_hash:
                prediction_cache[cache_key] = predictions
        last_failures[:] = list(predictions.attrs.get("run_failures", []))
        residuals: list[float] = []
        for target_name in selected_targets:
            if target_name not in df.columns or target_name not in predictions.columns:
                continue
            observed = pd.to_numeric(df[target_name], errors="coerce")
            predicted = pd.to_numeric(predictions[target_name], errors="coerce")
            mask = observed.notna() & predicted.notna()
            scale = max(float(observed[mask].std()) if mask.any() else 1.0, 1.0)
            residuals.extend((weights.get(target_name, 1.0) * (predicted[mask] - observed[mask]) / scale).tolist())
        if last_failures:
            residuals.extend([failed_run_penalty] * len(last_failures))
        return np.array(residuals or [0.0], dtype=float)

    try:
        if method == "differential_evolution":
            de = differential_evolution(lambda x: float(np.sum(objective_vector(x) ** 2)), bounds.tolist(), maxiter=18, polish=False, seed=7)
            x_start = de.x
        else:
            x_start = x0
        fit = least_squares(objective_vector, x_start, bounds=(bounds[:, 0], bounds[:, 1]), max_nfev=max_nfev)
        fitted = unpack(fit.x)
        jacobian = getattr(fit, "jac", None)
    except Exception as exc:
        warnings.append(f"非线性拟合失败，已降级为默认参数：{exc}")
        fitted = default_params.copy()
        jacobian = None
    predictions = _predict_experiment_table(df, fitted, model_mode=model_mode, failed_run_penalty=failed_run_penalty)
    run_failures_df = pd.DataFrame(predictions.attrs.get("run_failures", []))
    residuals = _build_residuals(df, predictions)
    r2, mae = _metrics_from_residuals(residuals)
    train_test = _train_test_metrics(df, fitted, model_mode=model_mode)
    confidence = _confidence_proxy(fitted, residuals)
    interval = _confidence_interval_proxy(fitted, residuals, jacobian)
    correlation = _parameter_correlation_proxy(free_names, jacobian)
    return ParameterEstimationResult(
        target=target,
        method=method,
        fitted_params=fitted,
        default_params=default_params,
        residuals=residuals,
        r2=r2,
        mae=mae,
        train_test_metrics=train_test,
        confidence=confidence,
        confidence_interval=interval,
        parameter_correlation=correlation,
        dataset_id=dataset_id,
        warnings=warnings,
        run_failures=run_failures_df,
        fitting_runtime_s=time.perf_counter() - started_at,
        model_mode=model_mode,
    )


def _predict_experiment_table(
    df: pd.DataFrame,
    params: dict[str, float],
    *,
    fit_against_flowsheet: bool = False,
    fit_against_dynamic: bool = False,
    model_mode: str = "empirical_proxy",
    failed_run_penalty: float = 8.0,
) -> pd.DataFrame:
    """Predict key experiment outputs from compact engineering correlations."""
    if model_mode == "empirical_proxy":
        if fit_against_dynamic:
            model_mode = "dynamic_ode_real"
        elif fit_against_flowsheet:
            model_mode = "flowsheet_real"
    if model_mode not in MODEL_MODES:
        model_mode = "empirical_proxy"
    rows = []
    failures: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        proxy = _predict_proxy_row(row, params)
        try:
            if model_mode == "flowsheet_real":
                pred = _predict_flowsheet_row(row, params)
            elif model_mode == "dynamic_ode_real":
                pred = _predict_dynamic_row(row, params)
            elif model_mode == "hybrid":
                flow = _predict_flowsheet_row(row, params)
                dyn = _predict_dynamic_row(row, params)
                pred = _blend_predictions(flow, dyn, 0.55)
            else:
                pred = proxy
        except Exception as exc:
            failures.append(
                {
                    "run_id": row.get("run_id", ""),
                    "model_mode": model_mode,
                    "error": str(exc),
                    "penalty": failed_run_penalty,
                }
            )
            pred = proxy.copy()
            pred["model_failed"] = True
        pred.setdefault("run_id", row.get("run_id", "unknown"))
        rows.append(pred)
    out = pd.DataFrame(rows)
    out.attrs["run_failures"] = failures
    return out


def _predict_proxy_row(row: pd.Series, params: dict[str, float]) -> dict[str, float | str | bool]:
    """Predict one experiment with the fast empirical proxy."""
    e = max(float(row.get("ethylene_feed", 0.0) or 0.0), 0.0) / 28.054
    p = max(float(row.get("propylene_feed", 0.0) or 0.0), 0.0) / 42.081
    enb = max(float(row.get("enb_feed", 0.0) or 0.0), 0.0) / 120.19
    pressure = float(row.get("pressure_MPa", 0.7) or 0.7)
    temperature = float(row.get("temperature_C", 100.0) or 100.0)
    h2 = max(float(row.get("hydrogen_feed", 0.0) or 0.0), 0.0)
    alti = max(float(row.get("AlTi_ratio", 500.0) or 500.0), 1.0)
    bht = max(float(row.get("BHT_ratio", 0.0) or 0.0), 0.0)
    k_e = params["k_E_ref"] / 3.6e6
    k_p = params["k_P_ref"] / 1.45e6
    k_d = params["k_ENB_ref"] / 4.0e6
    pressure_penalty = 1.0 / (1.0 + params["beta_P"] * max(pressure - params["pressure_optimum_MPa"], 0.0))
    ethylene_comp = 1.0 / (1.0 + params["beta_E"] * safe_divide(e, max(enb, 1.0e-9), 0.0))
    scores = {
        "C2": e * k_e,
        "C3": p * k_p,
        "ENB": enb * k_d * params["enb_feed_slope"] * pressure_penalty * ethylene_comp,
    }
    total = max(sum(scores.values()), 1.0e-12)
    c2 = 100.0 * scores["C2"] / total
    enb_wt = clamp(100.0 * scores["ENB"] / total, 0.0, 25.0)
    c3 = max(100.0 - c2 - enb_wt, 0.0)
    temp_factor = math.exp(-0.004 * (temperature - 100.0))
    bht_factor = 1.0 + 0.10 * safe_divide(bht, 1.0 + bht, 0.0)
    mw = params["Mw0"] * temp_factor * bht_factor / (1.0 + params["ktr_H2"] * h2 / 1000.0)
    pdi = clamp(2.7 + 0.002 * max(alti - 500.0, 0.0) / 10.0 + 0.000001 * params["kd_h"] * mw, 2.2, 5.2)
    mooney = estimate_mooney(mw, pdi, c2, enb_wt)
    activity = params["activity_decay_factor"] * (0.35 * k_e + 0.25 * k_p + 0.40 * k_d) * alti / (300.0 + alti) * math.exp(-params["kd_h"] * 0.5)
    activity *= 8.0
    polymer_g = float(row.get("polymer_g", 0.0) or 0.0)
    if polymer_g <= 0:
        feed_mass = max(float(row.get("ethylene_feed", 0.0) or 0.0) + float(row.get("propylene_feed", 0.0) or 0.0) + float(row.get("enb_feed", 0.0) or 0.0), 1.0)
        polymer_g = feed_mass * clamp(activity / 12.0, 0.05, 0.95)
    return {
        "run_id": row.get("run_id", "unknown"),
        "C2_wt": c2,
        "C3_wt": c3,
        "ENB_wt": enb_wt,
        "Mw": mw,
        "PDI": pdi,
        "Mooney": mooney,
        "activity": activity,
        "polymer_g": polymer_g,
        "conversion_E": clamp(activity * 7.0, 0.0, 98.0),
        "conversion_P": clamp(activity * 4.0, 0.0, 98.0),
        "conversion_ENB": clamp(activity * 5.5 * pressure_penalty, 0.0, 98.0),
        "dynamic_T_profile": temperature,
        "dynamic_Q_profile": activity,
        "model_failed": False,
    }


def _params_to_kinetics(params: dict[str, float]) -> KineticParameters:
    """Build a KineticParameters object from estimated parameters."""
    base = model_dump_compat(KineticParameters())
    for key in ["k_E_ref", "k_P_ref", "k_ENB_ref", "beta_P", "beta_E", "Mw0", "ktr_H2", "kd_h"]:
        if key in params:
            base[key] = float(params[key])
    return KineticParameters(**base)


def _config_from_experiment_row(row: pd.Series) -> Any:
    """Create a ProcessConfig from a normalized experiment row without mutating global state."""
    from .flowsheet import ProcessConfig

    e = max(float(row.get("ethylene_feed", 0.0) or row.get("ethylene_g", 20.0) or 20.0), 0.01)
    p = max(float(row.get("propylene_feed", 0.0) or row.get("propylene_g", 30.0) or 30.0), 0.01)
    d = max(float(row.get("enb_feed", 0.0) or row.get("enb_ml", 3.0) or 3.0), 0.0)
    scale = 20.0 / max(e + p + d, 1.0)
    return ProcessConfig(
        temperature_C=float(row.get("temperature_C", 100.0) or 100.0),
        pressure_MPa=float(row.get("pressure_MPa", 1.0) or 1.0),
        reactor_volume_L=float(row.get("reactor_scale_L", 5.0) or 5.0),
        residence_time_min=float(row.get("residence_time_min", 30.0) or 30.0),
        solvent=str(row.get("solvent", "hexane") or "hexane"),
        ethylene_kg_h=e * scale,
        propylene_kg_h=p * scale,
        enb_kg_h=d * scale,
        hydrogen_g_h=float(row.get("hydrogen_feed", 5.0) or 5.0),
        AlTi_ratio=float(row.get("AlTi_ratio", 1000.0) or 1000.0),
        BHT_ratio=float(row.get("BHT_ratio", 0.0) or 0.0),
        catalyst_umol_h=100.0,
    )


def _predict_flowsheet_row(row: pd.Series, params: dict[str, float]) -> dict[str, float | str | bool]:
    """Call the real flowsheet model for a row and return target predictions."""
    from .flowsheet import run_flowsheet

    cfg = _config_from_experiment_row(row)
    sim = run_flowsheet(cfg, kinetic_params_override=_params_to_kinetics(params))
    k = sim.kpis
    return {
        "run_id": row.get("run_id", "unknown"),
        "C2_wt": float(k["C2_wt"]),
        "C3_wt": float(k["C3_wt"]),
        "ENB_wt": float(k["ENB_wt"]),
        "Mw": float(k["Mw"]),
        "PDI": float(k["PDI"]),
        "Mooney": float(k["Mooney"]),
        "activity": float(k["catalyst_productivity_g_mol_h"]) / 1.0e7,
        "polymer_g": float(k["polymer_kg_h"]) * 1000.0,
        "conversion_E": float(k["C2_conversion_pct"]),
        "conversion_P": float(k["C3_conversion_pct"]),
        "conversion_ENB": float(k["ENB_conversion_pct"]),
        "dynamic_T_profile": float(cfg.temperature_C),
        "dynamic_Q_profile": float(k["heat_duty_kW"]),
        "model_failed": False,
    }


def _predict_dynamic_row(row: pd.Series, params: dict[str, float]) -> dict[str, float | str | bool]:
    """Call the real dynamic semi-batch ODE model for a row and return endpoint targets."""
    from .reactor import simulate_dynamic_semibatch_ode

    cfg = _config_from_experiment_row(row)
    dyn = simulate_dynamic_semibatch_ode(
        cfg,
        {
            "total_time_min": max(float(getattr(cfg, "residence_time_min", 30.0)), 30.0),
            "n_eval": 35,
        },
        params=_params_to_kinetics(params),
    )
    last = dyn.profile.iloc[-1]
    return {
        "run_id": row.get("run_id", "unknown"),
        "C2_wt": float(last.get("C2_wt", 0.0)),
        "C3_wt": float(last.get("C3_wt", 0.0)),
        "ENB_wt": float(last.get("ENB_wt", 0.0)),
        "Mw": float(last.get("Mw", 0.0)),
        "PDI": float(last.get("PDI", 0.0)),
        "Mooney": float(last.get("Mooney", 0.0)),
        "activity": max(float(last.get("conversion_pct", 0.0)) / 12.0, 0.0),
        "polymer_g": float(last.get("solids_wt", 0.0)) * 10.0,
        "conversion_E": float(last.get("conversion_E", 0.0)),
        "conversion_P": float(last.get("conversion_P", 0.0)),
        "conversion_ENB": float(last.get("conversion_ENB", 0.0)),
        "dynamic_T_profile": float(dyn.profile["T_C"].max()),
        "dynamic_Q_profile": float(dyn.profile["Q_rxn_kW"].max()),
        "model_failed": False,
    }


def _blend_predictions(a: dict[str, Any], b: dict[str, Any], a_weight: float) -> dict[str, Any]:
    """Blend two prediction dictionaries."""
    out = dict(a)
    for key, value in b.items():
        if isinstance(value, (int, float)) and isinstance(out.get(key), (int, float)):
            out[key] = a_weight * float(out[key]) + (1.0 - a_weight) * float(value)
    out["model_failed"] = bool(a.get("model_failed", False) or b.get("model_failed", False))
    return out


def _build_residuals(df: pd.DataFrame, predictions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    merged = df.merge(predictions, on="run_id", suffixes=("_observed", "_predicted"))
    for _, row in merged.iterrows():
        for target in TARGET_COLUMNS:
            observed = row.get(f"{target}_observed", np.nan)
            predicted = row.get(f"{target}_predicted", np.nan)
            if pd.notna(observed) and pd.notna(predicted):
                rows.append(
                    {
                        "run_id": row["run_id"],
                        "target": target,
                        "observed": float(observed),
                        "predicted": float(predicted),
                        "residual": float(predicted - observed),
                    }
                )
    return pd.DataFrame(rows)


def _metrics_from_residuals(residuals: pd.DataFrame) -> tuple[dict[str, float], dict[str, float]]:
    r2: dict[str, float] = {}
    mae: dict[str, float] = {}
    for target, group in residuals.groupby("target"):
        observed = group["observed"].to_numpy(dtype=float)
        predicted = group["predicted"].to_numpy(dtype=float)
        ss_res = float(np.sum((predicted - observed) ** 2))
        ss_tot = float(np.sum((observed - observed.mean()) ** 2))
        r2[target] = 1.0 - safe_divide(ss_res, ss_tot, 0.0) if ss_tot > 1.0e-12 else float("nan")
        mae[target] = float(np.mean(np.abs(predicted - observed)))
    return r2, mae


def _train_test_metrics(df: pd.DataFrame, params: dict[str, float], model_mode: str = "empirical_proxy") -> pd.DataFrame:
    """Return a deterministic train/test split metric proxy."""
    if len(df) < 4:
        return pd.DataFrame([{"split": "all", "target": "combined", "mae": np.nan, "r2": np.nan}])
    indexed = df.reset_index(drop=True)
    train = indexed.iloc[[i for i in range(len(indexed)) if i % 4 != 0]].copy()
    test = indexed.iloc[[i for i in range(len(indexed)) if i % 4 == 0]].copy()
    rows = []
    for split_name, split_df in [("train", train), ("test", test)]:
        residuals = _build_residuals(split_df, _predict_experiment_table(split_df, params, model_mode=model_mode))
        r2, mae = _metrics_from_residuals(residuals)
        for target_name in sorted(mae):
            rows.append({"split": split_name, "target": target_name, "mae": mae[target_name], "r2": r2.get(target_name)})
    return pd.DataFrame(rows)


def _confidence_proxy(params: dict[str, float], residuals: pd.DataFrame) -> pd.DataFrame:
    """Build a simple confidence proxy based on residual coverage and bound proximity."""
    n_points = max(int(residuals["run_id"].nunique()) if not residuals.empty else 0, 1)
    rows = []
    for name in ESTIMATED_PARAMETER_NAMES:
        low, high = DEFAULT_BOUNDS[name]
        value = params[name]
        center_penalty = abs((value - low) / max(high - low, 1.0e-12) - 0.5) * 2.0
        coverage = clamp(n_points / 12.0, 0.15, 1.0)
        confidence = clamp(coverage * (1.0 - 0.55 * center_penalty), 0.05, 0.95)
        rows.append({"parameter": name, "value": value, "confidence_proxy": confidence, "bound_low": low, "bound_high": high})
    return pd.DataFrame(rows)


def _confidence_interval_proxy(params: dict[str, float], residuals: pd.DataFrame, jacobian: Any | None) -> pd.DataFrame:
    """Return approximate confidence intervals from Jacobian or residual spread."""
    residual_scale = float(residuals["residual"].std()) if residuals is not None and not residuals.empty else 1.0
    rows = []
    if jacobian is not None:
        try:
            jtj_inv = np.linalg.pinv(np.asarray(jacobian).T @ np.asarray(jacobian))
            diag = np.sqrt(np.clip(np.diag(jtj_inv), 0.0, np.inf))
            for name, sigma in zip(ESTIMATED_PARAMETER_NAMES, np.resize(diag, len(ESTIMATED_PARAMETER_NAMES))):
                value = params[name]
                width = abs(value) * min(float(sigma) * 0.15, 0.5)
                rows.append({"parameter": name, "estimate": value, "low": value - width, "high": value + width, "method": "jacobian"})
            return pd.DataFrame(rows)
        except Exception:
            pass
    for name in ESTIMATED_PARAMETER_NAMES:
        value = params[name]
        width = max(abs(value) * 0.10, residual_scale * 0.01)
        rows.append({"parameter": name, "estimate": value, "low": value - width, "high": value + width, "method": "bootstrap_proxy"})
    return pd.DataFrame(rows)


def _parameter_correlation_proxy(free_names: list[str], jacobian: Any | None) -> pd.DataFrame:
    """Return a parameter-correlation matrix from Jacobian or identity fallback."""
    names = free_names or ESTIMATED_PARAMETER_NAMES
    if jacobian is not None:
        try:
            cov = np.linalg.pinv(np.asarray(jacobian).T @ np.asarray(jacobian))
            diag = np.clip(np.abs(np.diag(cov)), 1.0e-30, np.inf)
            denom = np.sqrt(np.outer(diag, diag))
            corr = np.divide(cov, denom, out=np.eye(cov.shape[0]), where=denom > 0)
            return pd.DataFrame(corr, index=names[: corr.shape[0]], columns=names[: corr.shape[1]]).reset_index(names="parameter")
        except Exception:
            pass
    return pd.DataFrame(np.eye(len(names)), index=names, columns=names).reset_index(names="parameter")
