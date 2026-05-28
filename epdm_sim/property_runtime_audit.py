"""Audit calibrated property-model runtime effects for V6.4."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .calibrated_property_models import CalibratedPropertyModel
from .property_model_runtime import property_model_runtime_dataframe
from .property_runtime_context import property_runtime_context_dataframe
from .residual_system import build_flowsheet_residual_system, residual_system_acceptance


def property_runtime_audit_dataframe(
    result: Any | None = None,
    *,
    conditions: dict[str, float] | None = None,
    models: list[CalibratedPropertyModel] | None = None,
    enable_calibrated: bool = True,
) -> pd.DataFrame:
    """Return runtime property audit rows with residual acceptance status."""
    runtime = property_model_runtime_dataframe(conditions=conditions, models=models, enable_calibrated=enable_calibrated)
    context = property_runtime_context_dataframe(result, conditions=conditions, models=models, enable_calibrated=enable_calibrated)
    residual_status = residual_system_acceptance(build_flowsheet_residual_system(result)) if result is not None else {"passed": True, "overall_score": 100.0, "critical_count": 0}
    rows = []
    for _, row in runtime.iterrows():
        base = float(row.get("base_value", row.get("base_Cstar_mol_L", row.get("base_heat_kJ_h", 0.0))) or 0.0)
        runtime_value = row.get("runtime_value", row.get("bridged_value", base))
        try:
            changed = abs(float(runtime_value) - base) > 1.0e-12
        except Exception:
            changed = False
        rows.append(
            {
                "property": row.get("property", row.get("parameter_type", "")),
                "model_id": row.get("model_id", ""),
                "source_type": row.get("source_type", ""),
                "runtime_value": runtime_value,
                "unit": row.get("unit", ""),
                "changed_from_default": changed,
                "within_validity": bool(row.get("within_validity", True)),
                "finite_runtime": bool(np.isfinite(float(runtime_value))) if isinstance(runtime_value, (int, float, np.number)) else True,
                "residual_score": float(residual_status["overall_score"]),
                "critical_residual_count": int(residual_status["critical_count"]),
                "passed": bool(row.get("passed", True) and residual_status["passed"]),
            }
        )
    if context.empty:
        return pd.DataFrame(rows)
    for _, row in context.iterrows():
        rows.append(
            {
                "property": "runtime_context",
                "model_id": row.get("model_id", ""),
                "source_type": row.get("source_type", ""),
                "runtime_value": row.get("runtime_value", 0.0),
                "unit": row.get("unit", ""),
                "changed_from_default": bool(row.get("runtime_changed_count", 0) > 0),
                "within_validity": bool(row.get("within_validity", True)),
                "finite_runtime": bool(row.get("finite_runtime", True)),
                "residual_score": float(row.get("residual_score", residual_status["overall_score"])),
                "critical_residual_count": int(row.get("critical_residual_count", residual_status["critical_count"])),
                "passed": bool(row.get("passed", True)),
            }
        )
    return pd.DataFrame(rows)


def property_runtime_audit_summary(
    result: Any | None = None,
    *,
    conditions: dict[str, float] | None = None,
    models: list[CalibratedPropertyModel] | None = None,
) -> dict[str, Any]:
    """Return compact property runtime audit status."""
    df = property_runtime_audit_dataframe(result, conditions=conditions, models=models)
    changed = int(df.get("changed_from_default", pd.Series(dtype=bool)).astype(bool).sum()) if not df.empty else 0
    failed = int((~df.get("passed", pd.Series(dtype=bool)).astype(bool)).sum()) if not df.empty else 1
    return {"passed": bool(failed == 0), "rows": int(len(df)), "changed_from_default": changed, "failed": failed}


def property_runtime_audit_gate(result: Any | None = None) -> dict[str, Any]:
    """Return release-gate status for property runtime audit."""
    return property_runtime_audit_summary(result)

