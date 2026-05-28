"""V6.0 math-core confidence composition helpers."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def combine_confidence_components(components: dict[str, float], weights: dict[str, float] | None = None) -> float:
    """Return a bounded weighted confidence score."""
    weights = weights or {key: 1.0 for key in components}
    total_weight = sum(max(float(weights.get(key, 0.0)), 0.0) for key in components) or 1.0
    value = sum(float(components[key]) * max(float(weights.get(key, 0.0)), 0.0) for key in components) / total_weight
    return float(np.clip(value, 0.0, 100.0))


def model_confidence_kernel_dataframe(components: dict[str, float] | None = None) -> pd.DataFrame:
    """Return default model-confidence components for report/gate use."""
    components = components or {
        "residual_acceptance": 90.0,
        "equation_binding": 100.0,
        "unit_safety": 100.0,
        "validity_envelope": 85.0,
        "benchmark_evidence": 60.0,
    }
    score = combine_confidence_components(components)
    rows: list[dict[str, Any]] = [{"component": key, "score": float(value), "passed": 0.0 <= float(value) <= 100.0} for key, value in components.items()]
    rows.append({"component": "combined", "score": score, "passed": bool(np.isfinite(score) and 0.0 <= score <= 100.0)})
    return pd.DataFrame(rows)
