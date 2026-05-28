"""Physical-constraint aggregation for the V5.7 math core."""

from __future__ import annotations

from typing import Any

import pandas as pd

from ..phase_equilibrium_constraints import phase_equilibrium_constraints_dataframe
from ..transport_core import transport_physical_constraints_dataframe
from ..validity_envelope import run_validity_envelope_for_config, validity_envelope_dataframe


def physical_constraints_dataframe(result: Any | None = None, *, config: Any | None = None) -> pd.DataFrame:
    """Return phase, transport and validity constraints in one table."""
    frames = []
    phase = phase_equilibrium_constraints_dataframe(result)
    if not phase.empty:
        frames.append(phase.assign(domain="phase_equilibrium"))
    transport = transport_physical_constraints_dataframe()
    if not transport.empty:
        frames.append(transport.assign(domain="transport"))
    if config is not None:
        validity = validity_envelope_dataframe(run_validity_envelope_for_config(config))
        if not validity.empty:
            validity = validity.rename(columns={"status": "validity_status"})
            validity["passed"] = ~validity["validity_status"].astype(str).str.contains("outside", case=False, na=False)
            frames.append(validity.assign(domain="validity_envelope"))
    return pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()


def physical_constraints_acceptance(result: Any | None = None, *, config: Any | None = None) -> dict[str, Any]:
    """Return pass/fail summary for aggregated physical constraints."""
    df = physical_constraints_dataframe(result, config=config)
    if df.empty:
        return {"passed": False, "rows": 0, "failed": 0}
    failed = int((~df.get("passed", pd.Series(dtype=bool)).fillna(True).astype(bool)).sum())
    return {"passed": failed == 0, "rows": int(len(df)), "failed": failed}

