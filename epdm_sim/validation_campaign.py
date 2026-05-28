"""Engineering validation-campaign closure utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from .flowsheet import ProcessConfig, run_flowsheet
from .utils import clamp, data_path, load_json, model_dump_compat


@dataclass
class ValidationCampaignResult:
    """Validation campaign scorecard."""

    validation_score: float
    model_bias: pd.DataFrame
    residuals: pd.DataFrame
    recommended_next_data: pd.DataFrame
    warnings: list[str] = field(default_factory=list)

    def as_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "validation_score": self.validation_score,
                    "n_residuals": len(self.residuals),
                    "n_recommendations": len(self.recommended_next_data),
                    "warnings": "; ".join(self.warnings),
                }
            ]
        )


def load_validation_datasets() -> dict[str, Any]:
    """Load validation dataset definitions from data/validation_datasets.json."""
    try:
        payload = load_json(data_path("validation_datasets.json"))
    except Exception:
        payload = {"datasets": []}
    payload.setdefault("datasets", [])
    return payload


def validation_datasets_dataframe() -> pd.DataFrame:
    """Return configured validation datasets as a table."""
    return pd.DataFrame(load_validation_datasets().get("datasets", []))


def _predict_default_kpis(config: ProcessConfig | None = None) -> dict[str, float]:
    result = run_flowsheet(config or ProcessConfig())
    return {key: float(value) for key, value in result.kpis.items() if isinstance(value, (int, float))}


def run_validation_campaign(
    endpoint_data: pd.DataFrame | None = None,
    *,
    config: ProcessConfig | None = None,
    target_columns: list[str] | None = None,
) -> ValidationCampaignResult:
    """Compare endpoint validation data to current model predictions.

    This is a lightweight closure layer: it uses existing endpoint data and the
    current flowsheet only.  It does not run ODE/CFD/optimization.
    """
    warnings: list[str] = []
    targets = target_columns or ["C2_wt", "ENB_wt", "Mooney", "Mw", "polymer_kg_h"]
    predicted = _predict_default_kpis(config)
    if endpoint_data is None or endpoint_data.empty:
        payload = load_validation_datasets()
        rows = []
        for dataset in payload.get("datasets", []):
            rows.extend(dataset.get("endpoint_rows", []))
        endpoint_data = pd.DataFrame(rows)
    if endpoint_data.empty:
        warnings.append("no endpoint validation data supplied; score reflects missing validation campaign.")
        return ValidationCampaignResult(
            35.0,
            pd.DataFrame(columns=["metric", "bias"]),
            pd.DataFrame(columns=["metric", "observed", "predicted", "residual"]),
            recommend_next_validation_data(pd.DataFrame(), warnings=["missing validation endpoints"]),
            warnings,
        )
    residual_rows = []
    for metric in targets:
        if metric not in endpoint_data.columns or metric not in predicted:
            continue
        observed_values = pd.to_numeric(endpoint_data[metric], errors="coerce").dropna()
        for observed in observed_values:
            residual_rows.append({"metric": metric, "observed": float(observed), "predicted": predicted[metric], "residual": float(observed) - predicted[metric]})
    residuals = pd.DataFrame(residual_rows)
    if residuals.empty:
        warnings.append("validation dataset did not contain comparable KPI columns.")
        score = 40.0
        bias = pd.DataFrame(columns=["metric", "bias", "mae"])
    else:
        bias = residuals.groupby("metric", as_index=False).agg(bias=("residual", "mean"), mae=("residual", lambda s: float(np.mean(np.abs(s)))))
        normalized_error = float(np.mean(np.abs(residuals["residual"]) / np.maximum(np.abs(residuals["observed"]), 1.0)))
        score = float(clamp(100.0 * (1.0 - normalized_error), 0.0, 100.0))
    return ValidationCampaignResult(score, bias, residuals, recommend_next_validation_data(bias), warnings)


def recommend_next_validation_data(model_bias: pd.DataFrame, warnings: list[str] | None = None) -> pd.DataFrame:
    """Recommend next validation data based on observed model bias."""
    rows = []
    warning_text = "; ".join(warnings or [])
    if model_bias.empty:
        rows.append({"priority": 1, "data_type": "endpoint", "recommendation": "Add endpoint C2/ENB/Mooney/Mw/polymer_kg_h validation rows.", "rationale": warning_text or "No comparable validation residuals."})
        rows.append({"priority": 2, "data_type": "time_series", "recommendation": "Add T/P/Q/solids time-series for one semi-batch recipe.", "rationale": "Dynamic model confidence remains limited without profile data."})
        return pd.DataFrame(rows)
    for idx, row in model_bias.sort_values("mae", ascending=False).head(4).iterrows():
        metric = str(row["metric"])
        rows.append(
            {
                "priority": len(rows) + 1,
                "data_type": "endpoint" if metric not in {"T_C", "Q_rxn_kW"} else "time_series",
                "recommendation": f"Collect additional validation data for {metric}.",
                "rationale": f"Current mean bias={row['bias']:.4g}, MAE={row['mae']:.4g}.",
            }
        )
    rows.append({"priority": len(rows) + 1, "data_type": "property", "recommendation": "Pair validation endpoints with rheology and calorimetry measurements.", "rationale": "Separates kinetic bias from property-model bias."})
    return pd.DataFrame(rows)
