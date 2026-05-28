"""Experimental and standard-case benchmark metadata for V5.4."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from .utils import data_path


def load_experimental_benchmarks() -> list[dict[str, Any]]:
    """Load experimental/literature/synthetic benchmark records."""
    path = Path(data_path("experimental_benchmarks.json"))
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def benchmark_data_hash(record: dict[str, Any]) -> str:
    """Return a stable hash for one benchmark record excluding stored hash."""
    payload = {key: value for key, value in record.items() if key != "data_hash"}
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def experimental_benchmarks_dataframe() -> pd.DataFrame:
    """Return experimental benchmark records with hash validation."""
    rows = []
    for record in load_experimental_benchmarks():
        row = dict(record)
        calculated = benchmark_data_hash(record)
        row["calculated_hash"] = calculated
        row["hash_matches"] = bool(not row.get("data_hash") or row.get("data_hash") == calculated)
        rows.append(row)
    return pd.DataFrame(rows)


def run_experimental_benchmark_checks(*, include_out_of_validity: bool = False) -> pd.DataFrame:
    """Run benchmark metadata acceptance checks without rerunning heavy models."""
    df = experimental_benchmarks_dataframe()
    if df.empty:
        return pd.DataFrame(columns=["benchmark_id", "passed", "severity", "message"])
    rows = []
    for _, row in df.iterrows():
        review_status = str(row.get("review_status", "")).lower()
        source_type = str(row.get("source_type", "regression_snapshot"))
        in_scope = include_out_of_validity or "out" not in review_status
        passed = bool(row.get("hash_matches", False) and in_scope and float(row.get("tolerance", 0.0)) >= 0.0)
        severity = "ok" if passed else ("warning" if not in_scope else "error")
        rows.append(
            {
                "benchmark_id": row.get("benchmark_id"),
                "source_type": source_type,
                "confidence_level": row.get("confidence_level", "low"),
                "passed": passed,
                "severity": severity,
                "message": "benchmark metadata accepted" if passed else "benchmark hash/status/tolerance requires review",
                "linked_equation_id": row.get("linked_equation_id", ""),
                "linked_residual_id": row.get("linked_residual_id", ""),
            }
        )
    return pd.DataFrame(rows)


def benchmark_confidence_score() -> float:
    """Return 0-100 benchmark confidence score from source confidence levels."""
    df = experimental_benchmarks_dataframe()
    if df.empty:
        return 0.0
    weights = {"low": 35.0, "medium": 60.0, "high": 85.0, "plant": 95.0}
    values = [weights.get(str(level).lower(), 35.0) for level in df.get("confidence_level", pd.Series(["low"] * len(df)))]
    return float(sum(values) / max(len(values), 1))

