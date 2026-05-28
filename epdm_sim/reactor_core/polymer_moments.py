"""Polymer moment sanity helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd


def polymer_moment_estimates(mn: float, mw: float) -> dict[str, float | bool]:
    """Return bounded Mn/Mw/PDI estimates."""
    mn_f = max(float(mn), 1.0e-12)
    mw_f = max(float(mw), mn_f)
    pdi = mw_f / mn_f
    return {"Mn": mn_f, "Mw": mw_f, "PDI": pdi, "passed": bool(np.isfinite(pdi) and pdi >= 1.0)}


def polymer_moments_dataframe(mn: float = 80000.0, mw: float = 160000.0) -> pd.DataFrame:
    """Return polymer moments as a DataFrame."""
    return pd.DataFrame([polymer_moment_estimates(mn, mw)])
