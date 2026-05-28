"""Dynamic state invariant projection helpers."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def project_state_invariants(state: dict[str, float]) -> dict[str, Any]:
    """Project inventory/T/P states into basic nonnegative invariants."""
    projected = {}
    corrections = 0
    for key, value in state.items():
        val = float(value)
        lower = 1.0e-9 if key in {"T_K", "P_Pa"} else 0.0
        new_val = max(val, lower)
        corrections += int(new_val != val)
        projected[key] = new_val
    return {"projected_state": projected, "corrections": corrections, "passed": corrections == 0 and all(np.isfinite(v) for v in projected.values())}


def invariant_projection_dataframe(state: dict[str, float] | None = None) -> pd.DataFrame:
    """Return invariant projection as rows."""
    result = project_state_invariants(state or {"liquid_mol": 1.0, "gas_mol": 1.0, "T_K": 350.0, "P_Pa": 1.0e6})
    rows = [{"state": key, "value": value, "corrections": result["corrections"], "passed": result["passed"]} for key, value in result["projected_state"].items()]
    return pd.DataFrame(rows)
