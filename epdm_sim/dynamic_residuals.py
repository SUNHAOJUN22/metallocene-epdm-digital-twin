"""Dynamic ODE residual time-series checks for V5.4."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd

from .residual_system import ResidualSystem, make_residual, score_residuals


@dataclass(frozen=True)
class DynamicResidualPoint:
    """One dynamic residual diagnostic row."""

    time_min: float
    residual_id: str
    value: float
    unit: str
    severity: str
    passed: bool
    physical_meaning: str
    suspected_source: str = ""
    suggested_fix: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def dynamic_residuals_dataframe(dynamic_result: Any) -> pd.DataFrame:
    """Calculate dynamic accumulation and reaction residuals from a profile."""
    profile = getattr(dynamic_result, "profile", pd.DataFrame())
    if profile is None or profile.empty:
        return pd.DataFrame(
            [
                DynamicResidualPoint(
                    0.0,
                    "dynamic_profile_missing",
                    1.0,
                    "-",
                    "warning",
                    False,
                    "dynamic profile should exist when ODE task has run",
                    "dynamic_ode",
                    "Run the dynamic template reactor before inspecting time-resolved residuals.",
                ).as_dict()
            ]
        )
    rows: list[DynamicResidualPoint] = []
    numeric = profile.select_dtypes(include="number")
    finite = bool(np.isfinite(numeric.to_numpy()).all())
    rows.append(DynamicResidualPoint(float(profile["time_min"].iloc[0]) if "time_min" in profile else 0.0, "dynamic_finiteness", 0.0 if finite else 1.0, "-", "ok" if finite else "error", finite, "all dynamic numeric states must remain finite", "dynamic_ode", "Inspect RHS terms and state scaling."))
    if "polymer_mass_kg" in profile:
        diff = profile["polymer_mass_kg"].diff().fillna(0.0)
        worst_drop = float(min(diff.min(), 0.0))
        rows.append(DynamicResidualPoint(float(profile["time_min"].iloc[-1]), "polymer_mass_monotonic", abs(worst_drop), "kg", "ok" if worst_drop >= -1.0e-10 else "error", worst_drop >= -1.0e-10, "polymer mass should be nondecreasing in polymerization", "dynamic_accumulation", "Check reaction consumption and nonnegative state projection."))
    rate_cols = [col for col in profile.columns if col.startswith("r_") and col.endswith("_mol_h")]
    if rate_cols:
        final_rate = float(profile[rate_cols].iloc[-1].abs().sum())
        quench_seen = bool("event" in profile and (profile["event"].astype(str) == "quench").any())
        passed = (not quench_seen) or final_rate <= 1.0e-8
        rows.append(DynamicResidualPoint(float(profile["time_min"].iloc[-1]), "quench_reaction_residual", final_rate, "mol/h", "ok" if passed else "error", passed, "reaction rate should approach zero after quench", "dynamic_quench", "Force catalyst activity and rate terms to zero after quench event."))
    if {"Q_rxn_kW", "T_K"}.issubset(profile.columns):
        heat_nonnegative = bool((profile["Q_rxn_kW"] >= -1.0e-12).all())
        rows.append(DynamicResidualPoint(float(profile["time_min"].iloc[-1]), "dynamic_heat_generation_nonnegative", float(max(-profile["Q_rxn_kW"].min(), 0.0)), "kW", "ok" if heat_nonnegative else "warning", heat_nonnegative, "exothermic polymerization heat generation is reported as positive removal demand", "heat_balance", "Check deltaH sign and kJ/h to kW conversion."))
    if "P_Pa" in profile:
        p_positive = bool((profile["P_Pa"] > 0.0).all())
        rows.append(DynamicResidualPoint(float(profile["time_min"].iloc[-1]), "dynamic_pressure_positive", float(max(0.0, -profile["P_Pa"].min())), "Pa", "ok" if p_positive else "error", p_positive, "dynamic pressure must remain positive", "pressure_control", "Check gas inventory and pressure control feed."))
    return pd.DataFrame([row.as_dict() for row in rows])


def dynamic_residual_system(dynamic_result: Any) -> ResidualSystem:
    """Build a ResidualSystem from dynamic residual rows."""
    df = dynamic_residuals_dataframe(dynamic_result)
    residuals = [
        make_residual(
            str(row["residual_id"]),
            str(row["physical_meaning"]),
            float(row["value"]),
            0.0,
            str(row["unit"]),
            1.0e-8 if str(row["residual_id"]) == "quench_reaction_residual" else 1.0e-6,
            str(row.get("suspected_source", "dynamic_ode")),
            str(row.get("suggested_fix", "Inspect dynamic residual diagnostics.")),
            "error" if str(row.get("severity")) == "error" else "warning",
        )
        for _, row in df.iterrows()
        if not bool(row.get("passed", False))
    ]
    return ResidualSystem(numerical_residuals=residuals, overall_score=score_residuals(residuals))


def dynamic_residual_acceptance(dynamic_result: Any) -> dict[str, Any]:
    """Return dynamic residual acceptance summary."""
    df = dynamic_residuals_dataframe(dynamic_result)
    failed = df[~df["passed"].astype(bool)] if "passed" in df else df
    critical_or_error = failed[failed["severity"].isin(["error", "critical"])] if not failed.empty else failed
    return {
        "passed": bool(critical_or_error.empty),
        "failed_count": int(len(failed)),
        "error_count": int(len(critical_or_error)),
        "max_residual": float(df["value"].abs().max()) if not df.empty and "value" in df else 0.0,
    }

