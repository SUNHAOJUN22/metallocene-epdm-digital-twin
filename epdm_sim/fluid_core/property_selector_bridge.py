"""Fluid-core bridge to calibrated property selection."""

from __future__ import annotations

import pandas as pd

from ..property_model_bridge import property_model_bridge_dataframe


def fluid_property_bridge_dataframe(temperature_C: float = 100.0) -> pd.DataFrame:
    """Return property-bridge rows for fluid calculations."""
    return property_model_bridge_dataframe(conditions={"temperature_C": float(temperature_C)})
