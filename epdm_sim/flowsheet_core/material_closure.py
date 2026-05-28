"""Flowsheet material-closure helpers."""

from __future__ import annotations

import pandas as pd


def material_closure_record(feed_kg_h: float, product_kg_h: float, vapor_kg_h: float = 0.0) -> dict[str, float | bool]:
    """Return material closure around flowsheet boundary."""
    lhs = float(feed_kg_h)
    rhs = float(product_kg_h) + float(vapor_kg_h)
    error = lhs - rhs
    return {"feed_kg_h": lhs, "product_kg_h": float(product_kg_h), "vapor_kg_h": float(vapor_kg_h), "error_kg_h": error, "passed": abs(error) <= max(1.0e-6, 0.10 * max(lhs, 1.0))}


def material_closure_dataframe(feed_kg_h: float = 1.0, product_kg_h: float = 1.0, vapor_kg_h: float = 0.0) -> pd.DataFrame:
    """Return material closure as a DataFrame."""
    return pd.DataFrame([material_closure_record(feed_kg_h, product_kg_h, vapor_kg_h)])
