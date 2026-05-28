"""Transport residual helpers for fluid-core split."""

from __future__ import annotations

import pandas as pd


def transport_residuals_dataframe(viscosity_Pa_s: float = 1.0e-3, pressure_drop_kPa: float = 1.0) -> pd.DataFrame:
    """Return simple positive transport residual checks."""
    rows = [
        {"residual_id": "viscosity_positive", "value": float(viscosity_Pa_s), "passed": float(viscosity_Pa_s) > 0.0},
        {"residual_id": "pressure_drop_nonnegative", "value": float(pressure_drop_kPa), "passed": float(pressure_drop_kPa) >= 0.0},
    ]
    return pd.DataFrame(rows)
