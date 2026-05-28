"""Dimension-signature validation for equation registry records."""

from __future__ import annotations

import pandas as pd

from ..equation_binding import equation_binding_dataframe


def dimension_signature_dataframe() -> pd.DataFrame:
    """Return equation dimensional signatures and unit completeness flags."""
    df = equation_binding_dataframe()
    if df.empty:
        return pd.DataFrame(columns=["equation_id", "dimensional_signature", "input_units", "output_unit", "passed"])
    out = df[["equation_id", "dimensional_signature", "input_units", "output_unit"]].copy()
    out["has_input_units"] = out["input_units"].map(lambda item: bool(item))
    out["has_output_unit"] = out["output_unit"].astype(str).str.len().gt(0)
    out["passed"] = out["dimensional_signature"].astype(str).str.len().gt(0) & out["has_input_units"] & out["has_output_unit"]
    return out


def validate_dimension_signatures() -> dict[str, int | bool]:
    """Return compact dimension-signature gate status."""
    df = dimension_signature_dataframe()
    failed = int((~df["passed"].astype(bool)).sum()) if not df.empty else 1
    return {"passed": failed == 0, "rows": int(len(df)), "failed": failed}
