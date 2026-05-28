"""Dynamic stability-region summaries."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from ..dynamic_core.stability_checks import dynamic_stability_checks_dataframe, stiffness_indicator_from_profile


def stability_region_record(dynamic_result: Any) -> dict[str, Any]:
    """Return a compact stability-region diagnostic."""
    stiffness = stiffness_indicator_from_profile(dynamic_result)
    checks = dynamic_stability_checks_dataframe(dynamic_result)
    failed = int((~checks["passed"].astype(bool)).sum()) if not checks.empty else 1
    return {
        "region_id": "bounded_dynamic_region",
        "stiffness_indicator": float(stiffness),
        "failed_checks": failed,
        "passed": bool(np.isfinite(stiffness) and failed == 0),
        "recommendation": "accepted" if failed == 0 else "reduce dt or use fallback with residual diagnostics",
    }


def stability_region_dataframe(dynamic_result: Any) -> pd.DataFrame:
    """Return dynamic stability-region rows."""
    return pd.DataFrame([stability_region_record(dynamic_result)])
