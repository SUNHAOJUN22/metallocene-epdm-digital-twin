"""Experiment data ingestion, normalization and quality checks.

This module is intentionally independent from Streamlit.  It turns local CSV
or Excel experiment files into a canonical calibration table and returns an
explicit quality report instead of failing on incomplete R&D datasets.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .utils import data_path, load_json


CANONICAL_FIELDS = [
    "run_id",
    "catalyst_id",
    "reactor_scale_L",
    "mode",
    "temperature_C",
    "pressure_MPa",
    "ethylene_feed",
    "propylene_feed",
    "enb_feed",
    "hydrogen_feed",
    "solvent",
    "AlTi_ratio",
    "BHT_ratio",
    "rpm",
    "residence_time_min",
    "polymer_g",
    "activity",
    "Mw",
    "PDI",
    "Mooney",
    "C2_wt",
    "C3_wt",
    "ENB_wt",
    "Tg_C",
    "Tm_C",
    "notes",
]

NUMERIC_FIELDS = [
    "reactor_scale_L",
    "temperature_C",
    "pressure_MPa",
    "ethylene_feed",
    "propylene_feed",
    "enb_feed",
    "hydrogen_feed",
    "AlTi_ratio",
    "BHT_ratio",
    "rpm",
    "residence_time_min",
    "polymer_g",
    "activity",
    "Mw",
    "PDI",
    "Mooney",
    "C2_wt",
    "C3_wt",
    "ENB_wt",
    "Tg_C",
    "Tm_C",
]

DEFAULTS = {
    "catalyst_id": "unknown",
    "reactor_scale_L": 2.0,
    "mode": "batch",
    "temperature_C": 100.0,
    "pressure_MPa": 0.7,
    "hydrogen_feed": 0.0,
    "solvent": "hexane",
    "AlTi_ratio": 500.0,
    "BHT_ratio": 0.0,
    "rpm": 500.0,
    "residence_time_min": 30.0,
    "notes": "",
}


@dataclass
class DataQualityReport:
    """Structured quality report for an experimental data table."""

    missing_fields: list[str] = field(default_factory=list)
    missing_values: dict[str, int] = field(default_factory=dict)
    outliers: list[dict[str, Any]] = field(default_factory=list)
    impossible_values: list[dict[str, Any]] = field(default_factory=list)
    duplicate_run_ids: list[str] = field(default_factory=list)
    recommended_fixes: list[str] = field(default_factory=list)

    @property
    def is_usable_for_calibration(self) -> bool:
        """Return whether the table has enough target data for calibration."""
        fatal = [field for field in ["run_id", "C2_wt", "ENB_wt", "Mw", "Mooney"] if field in self.missing_fields]
        return not fatal

    def as_dataframe(self) -> pd.DataFrame:
        """Return a flat diagnostic table for UI and Excel export."""
        rows: list[dict[str, Any]] = []
        for field in self.missing_fields:
            rows.append({"type": "missing_field", "field": field, "detail": "field absent", "count": None})
        for field, count in self.missing_values.items():
            if count:
                rows.append({"type": "missing_values", "field": field, "detail": "blank/NaN values", "count": count})
        for item in self.impossible_values:
            rows.append({"type": "impossible_value", **item})
        for item in self.outliers:
            rows.append({"type": "outlier", **item})
        for run_id in self.duplicate_run_ids:
            rows.append({"type": "duplicate_run_id", "field": "run_id", "detail": run_id, "count": None})
        for fix in self.recommended_fixes:
            rows.append({"type": "recommended_fix", "field": "", "detail": fix, "count": None})
        return pd.DataFrame(rows, columns=["type", "field", "detail", "count", "run_id", "value"])


def load_experiment_schema(path: str | Path | None = None) -> dict[str, Any]:
    """Load the canonical experiment schema JSON."""
    return load_json(path or data_path("experiment_schema.json"))


def load_experiment_file(path: str | Path) -> pd.DataFrame:
    """Load a local CSV or Excel experiment table."""
    source = Path(path)
    if source.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(source)
    return pd.read_csv(source)


def load_internal_experiment_dataset() -> pd.DataFrame:
    """Load and normalize the bundled internal experiment table."""
    return normalize_experiments(pd.read_csv(data_path("internal_experiments.csv")))


def normalize_experiments(df: pd.DataFrame, schema: dict[str, Any] | None = None) -> pd.DataFrame:
    """Normalize incoming experimental data to the canonical schema.

    Missing operating conditions are filled with conservative defaults so the
    table can still be used for trend calibration while the quality report
    records the gaps.
    """
    schema = schema or load_experiment_schema()
    aliases = schema.get("aliases", {})
    normalized = df.copy()
    rename_map = {col: aliases[col] for col in normalized.columns if col in aliases and aliases[col] not in normalized.columns}
    normalized = normalized.rename(columns=rename_map)
    if "notes" not in normalized.columns:
        normalized["notes"] = ""
    if "ep_ratio" in df.columns:
        normalized["notes"] = normalized["notes"].fillna("").astype(str) + " ep_ratio=" + df["ep_ratio"].astype(str)
    for field_name in CANONICAL_FIELDS:
        if field_name not in normalized.columns:
            normalized[field_name] = DEFAULTS.get(field_name, np.nan)
    for field_name, value in DEFAULTS.items():
        if field_name in normalized.columns:
            normalized[field_name] = normalized[field_name].fillna(value)
    for field_name in NUMERIC_FIELDS:
        normalized[field_name] = pd.to_numeric(normalized[field_name], errors="coerce")
    normalized["run_id"] = normalized["run_id"].astype(str)
    normalized["catalyst_id"] = normalized["catalyst_id"].fillna("unknown").astype(str)
    normalized["mode"] = normalized["mode"].fillna("batch").astype(str)
    normalized["solvent"] = normalized["solvent"].fillna("hexane").astype(str)
    normalized["notes"] = normalized["notes"].fillna("").astype(str)
    return normalized[CANONICAL_FIELDS]


def quality_check_experiments(df: pd.DataFrame, schema: dict[str, Any] | None = None) -> DataQualityReport:
    """Check schema coverage, missing values, duplicates, bounds and robust outliers."""
    schema = schema or load_experiment_schema()
    report = DataQualityReport()
    missing_fields = [field_name for field_name in CANONICAL_FIELDS if field_name not in df.columns]
    report.missing_fields.extend(missing_fields)
    normalized = normalize_experiments(df, schema)
    for field_name in CANONICAL_FIELDS:
        count = int(normalized[field_name].isna().sum())
        if count:
            report.missing_values[field_name] = count
    duplicate_mask = normalized["run_id"].duplicated(keep=False)
    report.duplicate_run_ids = sorted(normalized.loc[duplicate_mask, "run_id"].dropna().astype(str).unique().tolist())
    bounds = schema.get("numeric_bounds", {})
    for field_name, (low, high) in bounds.items():
        if field_name not in normalized.columns:
            continue
        values = pd.to_numeric(normalized[field_name], errors="coerce")
        bad = normalized.loc[(values < low) | (values > high), ["run_id", field_name]]
        for _, row in bad.iterrows():
            report.impossible_values.append(
                {
                    "field": field_name,
                    "run_id": row["run_id"],
                    "value": row[field_name],
                    "detail": f"outside [{low}, {high}]",
                    "count": None,
                }
            )
    for field_name in ["polymer_g", "activity", "Mw", "PDI", "Mooney", "C2_wt", "ENB_wt"]:
        series = pd.to_numeric(normalized[field_name], errors="coerce").dropna()
        if len(series) < 5:
            continue
        q1, q3 = series.quantile([0.25, 0.75])
        iqr = max(q3 - q1, 1.0e-12)
        low = q1 - 3.0 * iqr
        high = q3 + 3.0 * iqr
        outlier_rows = normalized.loc[(normalized[field_name] < low) | (normalized[field_name] > high), ["run_id", field_name]]
        for _, row in outlier_rows.iterrows():
            report.outliers.append(
                {
                    "field": field_name,
                    "run_id": row["run_id"],
                    "value": row[field_name],
                    "detail": "robust IQR outlier",
                    "count": None,
                }
            )
    if missing_fields:
        report.recommended_fixes.append("补齐缺失字段或在导入前建立字段映射。")
    if report.duplicate_run_ids:
        report.recommended_fixes.append("检查重复 run_id，保留原始编号并用 replicate 字段区分重复实验。")
    if report.impossible_values:
        report.recommended_fixes.append("修正超出工程范围的数值，尤其是组成、PDI、温度和压力单位。")
    missing_targets = [target for target in ["C2_wt", "ENB_wt", "Mw", "Mooney", "activity"] if normalized[target].notna().sum() < 3]
    if missing_targets:
        report.recommended_fixes.append(f"以下目标数据不足，校准可信度有限：{', '.join(missing_targets)}。")
    if not report.recommended_fixes:
        report.recommended_fixes.append("数据表可用于趋势校准；建议继续补充H2、压力和转化率字段。")
    return report


def calibration_subset(df: pd.DataFrame, targets: list[str] | None = None) -> pd.DataFrame:
    """Return rows with enough measured outputs for calibration."""
    normalized = normalize_experiments(df)
    target_cols = targets or ["C2_wt", "ENB_wt", "Mw", "Mooney", "activity"]
    available = normalized[target_cols].notna().sum(axis=1) >= max(1, min(2, len(target_cols)))
    feed_ok = normalized[["ethylene_feed", "propylene_feed", "enb_feed"]].notna().all(axis=1)
    return normalized.loc[available & feed_ok].copy()
