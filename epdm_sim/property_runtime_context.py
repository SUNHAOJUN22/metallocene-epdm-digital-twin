"""Property runtime context for V6.3 calibrated-model execution."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .calibrated_property_models import CalibratedPropertyModel
from .property_model_runtime import property_model_runtime_dataframe
from .residual_system import ResidualSystem, build_flowsheet_residual_system, residual_system_acceptance


def build_property_runtime_context(
    result_or_system: Any | None = None,
    *,
    conditions: dict[str, float] | None = None,
    models: list[CalibratedPropertyModel] | None = None,
    enable_calibrated: bool = True,
) -> dict[str, Any]:
    """Build property runtime context and residual-safety status."""
    df = property_model_runtime_dataframe(conditions=conditions, models=models, enable_calibrated=enable_calibrated)
    system = result_or_system if isinstance(result_or_system, ResidualSystem) else (build_flowsheet_residual_system(result_or_system) if result_or_system is not None else ResidualSystem())
    acceptance = residual_system_acceptance(system)
    changed = int((pd.to_numeric(df.get("runtime_value", pd.Series(dtype=float)), errors="coerce") != pd.to_numeric(df.get("base_value", pd.Series(dtype=float)), errors="coerce")).fillna(False).sum()) if not df.empty else 0
    passed = bool((df.empty or df.get("passed", pd.Series([True] * len(df))).astype(bool).all()) and acceptance["passed"])
    return {
        "property_model_rows": int(len(df)),
        "calibrated_enabled": bool(enable_calibrated),
        "runtime_changed_count": changed,
        "residual_score": float(acceptance["overall_score"]),
        "critical_residual_count": int(acceptance["critical_count"]),
        "passed": passed,
    }


def property_runtime_context_dataframe(
    result_or_system: Any | None = None,
    *,
    conditions: dict[str, float] | None = None,
    models: list[CalibratedPropertyModel] | None = None,
    enable_calibrated: bool = True,
) -> pd.DataFrame:
    """Return property runtime context rows joined with runtime property values."""
    context = build_property_runtime_context(result_or_system, conditions=conditions, models=models, enable_calibrated=enable_calibrated)
    runtime = property_model_runtime_dataframe(conditions=conditions, models=models, enable_calibrated=enable_calibrated)
    if runtime.empty:
        return pd.DataFrame([context])
    for key, value in context.items():
        runtime[key] = value
    runtime["finite_runtime"] = pd.to_numeric(runtime.get("runtime_value", pd.Series([0.0] * len(runtime))), errors="coerce").map(np.isfinite)
    return runtime


def property_runtime_context_summary(result_or_system: Any | None = None, **kwargs: Any) -> dict[str, Any]:
    """Return compact gate status for property runtime context."""
    df = property_runtime_context_dataframe(result_or_system, **kwargs)
    failed = 0 if df.empty else int((~df.get("passed", pd.Series([True] * len(df))).astype(bool)).sum())
    return {"passed": failed == 0, "rows": int(len(df)), "failed": failed}

