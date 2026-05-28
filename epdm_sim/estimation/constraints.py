"""Parameter-constraint tables for calibration workflows."""

from __future__ import annotations

import pandas as pd

from ..parameter_constraints import parameter_constraints_dataframe


def estimation_parameter_constraints() -> pd.DataFrame:
    """Return physical parameter constraints for estimation."""
    return parameter_constraints_dataframe()

