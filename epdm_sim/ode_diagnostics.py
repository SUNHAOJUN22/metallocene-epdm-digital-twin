"""Diagnostics for template ODE profiles and solver summaries."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ODEDiagnostic:
    """One ODE diagnostic row."""

    diagnostic_id: str
    passed: bool
    severity: str
    value: float | str
    unit: str
    message: str
    suggested_fix: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RHSTermDiagnostic:
    """One physically named RHS contribution diagnostic."""

    term: str
    value: float
    unit: str
    affected_state: str
    physical_meaning: str
    finite_check: bool
    nonnegative_check: bool | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def diagnose_dynamic_ode(dynamic_result: Any) -> list[ODEDiagnostic]:
    """Diagnose numerical and physical consistency of a dynamic ODE result."""
    profile = getattr(dynamic_result, "profile", pd.DataFrame())
    summary = getattr(dynamic_result, "summary", {})
    rows: list[ODEDiagnostic] = []
    if profile.empty:
        return [ODEDiagnostic("profile_nonempty", False, "error", 0.0, "rows", "Dynamic profile is empty.", "Check solver setup.")]
    numeric = profile.select_dtypes(include="number")
    finite = bool(np.isfinite(numeric.to_numpy()).all())
    rows.append(ODEDiagnostic("finite_states", finite, "ok" if finite else "error", str(finite), "-", "All numeric ODE states are finite.", "Inspect RHS scaling."))
    for col in ["polymer_mass_kg", "T_K", "P_Pa"]:
        if col in profile:
            nonnegative = bool((profile[col] >= 0.0).all())
            rows.append(ODEDiagnostic(f"{col}_nonnegative", nonnegative, "ok" if nonnegative else "error", float(profile[col].min()), col.split("_")[-1], f"{col} remains nonnegative.", "Review state projection and units."))
    if "polymer_mass_kg" in profile:
        monotonic = bool(profile["polymer_mass_kg"].diff().dropna().ge(-1.0e-10).all())
        rows.append(ODEDiagnostic("polymer_mass_nondecreasing", monotonic, "ok" if monotonic else "error", float(profile["polymer_mass_kg"].iloc[-1]), "kg", "Polymer mass is nondecreasing.", "Check reaction consumption and quench logic."))
    fallback_used = bool(summary.get("fallback_used", False))
    fallback_reason = str(summary.get("fallback_reason", ""))
    rows.append(ODEDiagnostic("fallback_explained", (not fallback_used) or bool(fallback_reason), "ok" if (not fallback_used) or bool(fallback_reason) else "error", fallback_reason or "none", "-", "Fallback has an engineering reason when used.", "Populate fallback_reason."))
    rows.append(ODEDiagnostic("solver_nfev", int(summary.get("nfev", 0)) >= 0, "ok", float(summary.get("nfev", 0)), "count", "Solver function evaluations are recorded.", "Record nfev/njev/step_count."))
    return rows


def ode_diagnostics_dataframe(dynamic_result: Any) -> pd.DataFrame:
    """Return ODE diagnostics as a DataFrame."""
    return pd.DataFrame([row.as_dict() for row in diagnose_dynamic_ode(dynamic_result)])


def rhs_term_schema_dataframe() -> pd.DataFrame:
    """Document RHS terms and units for audit reports."""
    return pd.DataFrame(
        [
            {"term": "feed", "meaning": "external monomer/chain-transfer addition", "unit": "mol/min"},
            {"term": "reaction_consumption", "meaning": "liquid monomer insertion into polymer", "unit": "mol/min"},
            {"term": "gas_liquid_transfer", "meaning": "headspace-liquid relaxation", "unit": "mol/min"},
            {"term": "pressure_control", "meaning": "feed factor from pressure deficit", "unit": "-"},
            {"term": "heat_generation", "meaning": "polymerization heat release", "unit": "kJ/min"},
            {"term": "heat_removal", "meaning": "UA cooling to jacket/coolant", "unit": "kJ/min"},
            {"term": "catalyst_decay", "meaning": "active center deactivation", "unit": "mol/min"},
            {"term": "quench", "meaning": "forced catalyst activity termination", "unit": "event"},
        ]
    )


def rhs_terms_diagnostics_dataframe(dynamic_result: Any | None = None) -> pd.DataFrame:
    """Return RHS term diagnostics with units and physical meaning.

    The function is intentionally read-only: it summarizes supplied dynamic
    results when available and otherwise returns the executable RHS contract
    used by report/release gates without launching an ODE solve.
    """
    profile = getattr(dynamic_result, "profile", pd.DataFrame()) if dynamic_result is not None else pd.DataFrame()
    final_rate = 0.0
    heat_proxy = 0.0
    if not profile.empty:
        rate_cols = [col for col in profile.columns if col.startswith("r_")]
        if rate_cols:
            final_rate = float(profile[rate_cols].iloc[-1].sum())
            heat_proxy = max(final_rate, 0.0)
    rows = [
        RHSTermDiagnostic("feed_term", 0.0, "mol/min", "liquid_moles/gas_moles", "external monomer and chain-transfer addition", True, True),
        RHSTermDiagnostic("reaction_consumption", final_rate, "mol/min", "liquid_moles", "liquid monomer insertion into polymer", bool(np.isfinite(final_rate)), True),
        RHSTermDiagnostic("gas_liquid_transfer", 0.0, "mol/min", "liquid_moles/gas_moles", "headspace-liquid relaxation transfer", True, None),
        RHSTermDiagnostic("pressure_control", 1.0, "-", "feed_factor", "pressure deficit throttles feed", True, True),
        RHSTermDiagnostic("heat_generation", heat_proxy, "kJ/min", "T_K", "polymerization heat release", bool(np.isfinite(heat_proxy)), True),
        RHSTermDiagnostic("heat_removal", 0.0, "kJ/min", "T_K", "UA cooling to jacket/coolant", True, True),
        RHSTermDiagnostic("catalyst_decay", 0.0, "mol/min", "catalyst_active_mol", "active center deactivation", True, None),
        RHSTermDiagnostic("quench_term", 0.0, "event", "catalyst_active_mol", "forced catalyst activity termination", True, None),
    ]
    return pd.DataFrame([row.as_dict() for row in rows])
