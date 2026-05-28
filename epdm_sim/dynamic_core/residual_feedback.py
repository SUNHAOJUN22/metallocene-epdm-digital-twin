"""Feed dynamic residuals back into solver diagnostics and fallback policy."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .residual_timeseries import dynamic_residual_timeseries


def dynamic_residual_feedback(dynamic_result: Any, *, critical_threshold: float = 1.0e3) -> pd.DataFrame:
    """Return residual severity rows for a dynamic result."""
    df = dynamic_residual_timeseries(dynamic_result)
    if df.empty:
        return pd.DataFrame([{"residual_id": "dynamic_profile_missing", "severity": "critical", "passed": False, "value": np.inf}])
    out = df.copy()
    value = pd.to_numeric(out.get("value", 0.0), errors="coerce").fillna(0.0).abs()
    out["severity"] = np.where(~out.get("passed", True).astype(bool), "error", np.where(value > critical_threshold, "critical", "ok"))
    out["requires_solver_warning"] = out["severity"].isin(["error", "critical"])
    return out


def residual_feedback_solver_status(dynamic_result: Any) -> dict[str, Any]:
    """Return solver status augmented with residual acceptance diagnostics."""
    feedback = dynamic_residual_feedback(dynamic_result)
    summary = dict(getattr(dynamic_result, "summary", {}) or {})
    residual_max = float(pd.to_numeric(feedback.get("value", pd.Series([0.0])), errors="coerce").fillna(0.0).abs().max())
    acceptance_rate = float(feedback.get("passed", pd.Series(dtype=bool)).astype(bool).mean()) if not feedback.empty else 0.0
    critical = int(feedback["severity"].isin(["critical", "error"]).sum()) if "severity" in feedback else 1
    return {
        "solver_mode_used": summary.get("solver_mode_used", summary.get("solver_mode", "unknown")),
        "fallback_used": bool(summary.get("fallback_used", False)),
        "fallback_reason": summary.get("fallback_reason", "" if critical == 0 else "dynamic residual feedback requested solver warning"),
        "nfev": int(summary.get("nfev", 0) or 0),
        "njev": int(summary.get("njev", 0) or 0),
        "step_count": int(summary.get("step_count", len(getattr(dynamic_result, "profile", []))) or 0),
        "residual_max_error": residual_max,
        "residual_acceptance_rate": acceptance_rate,
        "critical_residual_count": critical,
        "passed": bool(critical == 0 and np.isfinite(residual_max)),
    }


def residual_feedback_recommends_fallback(dynamic_result: Any) -> bool:
    """Return whether residual feedback should recommend solver fallback/warning."""
    status = residual_feedback_solver_status(dynamic_result)
    return bool(status["critical_residual_count"] > 0 or not np.isfinite(status["residual_max_error"]))

