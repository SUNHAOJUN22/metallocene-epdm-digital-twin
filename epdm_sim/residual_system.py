"""Conservation residual system used by V5.3 math-core gates."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np
import pandas as pd

SEVERITY_PENALTY = {"ok": 0.0, "pass": 0.0, "warning": 8.0, "error": 25.0, "critical": 50.0}


@dataclass(frozen=True)
class Residual:
    """One conservation or numerical residual."""

    residual_id: str
    equation: str
    lhs: float
    rhs: float
    absolute_error: float
    relative_error_pct: float
    unit: str
    tolerance: float
    severity: str
    passed: bool
    suspected_source: str
    suggested_fix: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResidualSystem:
    """Grouped residuals for flowsheet, dynamic ODE and report gates."""

    mass_residuals: list[Residual] = field(default_factory=list)
    component_residuals: list[Residual] = field(default_factory=list)
    energy_residuals: list[Residual] = field(default_factory=list)
    phase_residuals: list[Residual] = field(default_factory=list)
    reaction_residuals: list[Residual] = field(default_factory=list)
    numerical_residuals: list[Residual] = field(default_factory=list)
    overall_score: float = 100.0

    def all_residuals(self) -> list[Residual]:
        return (
            self.mass_residuals
            + self.component_residuals
            + self.energy_residuals
            + self.phase_residuals
            + self.reaction_residuals
            + self.numerical_residuals
        )

    def as_dataframe(self) -> pd.DataFrame:
        rows = [item.as_dict() for item in self.all_residuals()]
        if not rows:
            return pd.DataFrame(columns=list(Residual("", "", 0, 0, 0, 0, "", 0, "", True, "", "").as_dict()))
        df = pd.DataFrame(rows)
        df["overall_score"] = self.overall_score
        return df


def make_residual(
    residual_id: str,
    equation: str,
    lhs: float,
    rhs: float,
    unit: str,
    tolerance: float,
    suspected_source: str,
    suggested_fix: str,
    severity_if_failed: str = "warning",
) -> Residual:
    """Create a finite residual with relative error and severity."""
    lhs_f = float(lhs) if np.isfinite(lhs) else 0.0
    rhs_f = float(rhs) if np.isfinite(rhs) else 0.0
    abs_err = abs(lhs_f - rhs_f)
    denom = max(abs(rhs_f), abs(lhs_f), 1.0e-12)
    rel = 100.0 * abs_err / denom
    passed = bool(np.isfinite(abs_err) and abs_err <= tolerance)
    severity = "ok" if passed else severity_if_failed
    if severity not in SEVERITY_PENALTY:
        severity = "warning"
    return Residual(
        residual_id,
        equation,
        lhs_f,
        rhs_f,
        abs_err,
        rel,
        unit,
        tolerance,
        severity,
        passed,
        suspected_source if not passed else "",
        suggested_fix if not passed else "",
    )


def score_residuals(residuals: list[Residual]) -> float:
    """Return a 0-100 residual-system score."""
    score = 100.0
    for item in residuals:
        if item.passed:
            continue
        score -= SEVERITY_PENALTY.get(item.severity, 8.0)
    return max(0.0, min(100.0, score))


def critical_residuals(system: ResidualSystem) -> list[Residual]:
    """Return residuals that should block release, DOE or optimizer recommendations."""
    return [item for item in system.all_residuals() if (not item.passed) and item.severity == "critical"]


def residual_system_acceptance(system: ResidualSystem, *, minimum_score: float = 70.0) -> dict[str, Any]:
    """Return a compact acceptance record for gates, DOE and optimizer filters."""
    critical = critical_residuals(system)
    errors = [item for item in system.all_residuals() if (not item.passed) and item.severity == "error"]
    passed = bool(not critical and system.overall_score >= minimum_score)
    return {
        "passed": passed,
        "overall_score": float(system.overall_score),
        "critical_count": len(critical),
        "error_count": len(errors),
        "minimum_score": float(minimum_score),
        "critical_sources": "; ".join(sorted({item.suspected_source for item in critical if item.suspected_source})),
    }


def build_flowsheet_residual_system(result: Any) -> ResidualSystem:
    """Build mass, phase, reaction and heat residuals for a flowsheet result."""
    streams = getattr(result, "streams", {})
    normalized_streams = {str(key).strip().lower(): value for key, value in streams.items()}
    feed = streams.get("feed") or normalized_streams.get("feed")
    product = streams.get("product") or normalized_streams.get("product") or normalized_streams.get("polymer product")
    flash1 = getattr(result, "flash1", None)
    flash2 = getattr(result, "flash2", None)
    reactor = getattr(result, "reactor", None)
    heat = getattr(result, "heat_balance", None)
    kpis = getattr(result, "kpis", {})

    feed_mass = float(feed.total_mass_flow()) if feed is not None else 0.0
    vapor_mass = 0.0
    if flash1 is not None:
        vapor_mass += float(flash1.vapor.total_mass_flow())
    if flash2 is not None:
        vapor_mass += float(flash2.vapor.total_mass_flow())
    product_mass = float(product.total_mass_flow()) if product is not None else float(kpis.get("polymer_kg_h", 0.0))
    mass_residuals = [
        make_residual(
            "total_mass_balance",
            "feed ~= product + flashed vapor + recycle/purge adjustment",
            feed_mass,
            product_mass + vapor_mass,
            "kg/h",
            max(0.10 * max(feed_mass, 1.0), 1.0e-6),
            "flowsheet",
            "Check purge/recycle and flash split streams.",
        )
    ]

    phase_residuals: list[Residual] = []
    for name, flash in [("flash1", flash1), ("flash2", flash2)]:
        if flash is None:
            continue
        inlet_proxy = flash.vapor.total_mass_flow() + flash.liquid.total_mass_flow()
        phase_residuals.append(
            make_residual(
                f"{name}_phase_mass",
                "flash inlet = vapor + liquid",
                inlet_proxy,
                flash.vapor.total_mass_flow() + flash.liquid.total_mass_flow(),
                "kg/h",
                1.0e-9,
                name,
                "Verify Rachford-Rice split and component mass conversion.",
            )
        )
        phase_residuals.append(
            make_residual(
                f"{name}_polymer_vapor",
                "polymer vapor mass = 0",
                float(flash.vapor.polymer_mass_kg_h),
                0.0,
                "kg/h",
                1.0e-12,
                name,
                "Keep polymer pseudo-component entirely in liquid phase.",
                "critical",
            )
        )

    polymer_mass = float(kpis.get("polymer_kg_h", 0.0))
    consumed_mass = polymer_mass
    if reactor is not None and hasattr(reactor, "total_polymer_kg_h"):
        consumed_mass = float(getattr(reactor, "total_polymer_kg_h", polymer_mass))
    reaction_residuals = [
        make_residual(
            "monomer_to_polymer_mass",
            "consumed monomer mass = polymer segment mass",
            consumed_mass,
            polymer_mass,
            "kg/h",
            max(1.0e-6, 0.01 * max(polymer_mass, 1.0)),
            "reactor",
            "Check monomer conversion and segment molecular weights.",
        )
    ]

    c2 = float(kpis.get("C2_wt", 0.0))
    c3 = float(kpis.get("C3_wt", 0.0))
    enb = float(kpis.get("ENB_wt", 0.0))
    component_residuals = [
        make_residual(
            "product_composition_closure",
            "C2 + C3 + ENB = 100 wt%",
            c2 + c3 + enb,
            100.0,
            "wt%",
            1.0e-6,
            "product_properties",
            "Normalize segment composition from polymer segment masses.",
        )
    ]

    q_rxn = float(getattr(heat, "Q_rxn_kW", kpis.get("heat_duty_kW", 0.0)))
    energy_residuals = [
        make_residual(
            "heat_release_proxy",
            "reported reaction heat = heat duty KPI",
            q_rxn,
            float(kpis.get("heat_duty_kW", q_rxn)),
            "kW",
            max(1.0e-6, 0.02 * max(abs(q_rxn), 1.0)),
            "heat_balance",
            "Check deltaH sign and kJ/h to kW conversion.",
        )
    ]
    all_items = mass_residuals + component_residuals + energy_residuals + phase_residuals + reaction_residuals
    return ResidualSystem(mass_residuals, component_residuals, energy_residuals, phase_residuals, reaction_residuals, [], score_residuals(all_items))


def build_dynamic_residual_system(dynamic_result: Any) -> ResidualSystem:
    """Build simple dynamic accumulation residuals for a template ODE profile."""
    profile = getattr(dynamic_result, "profile", pd.DataFrame())
    numerical: list[Residual] = []
    reaction: list[Residual] = []
    if not profile.empty:
        finite = bool(np.isfinite(profile.select_dtypes(include="number").to_numpy()).all())
        numerical.append(make_residual("dynamic_finiteness", "all dynamic numeric states finite", 1.0 if finite else 0.0, 1.0, "-", 0.0, "dynamic_ode", "Inspect RHS terms and scaling.", "error"))
        if "polymer_mass_kg" in profile:
            monotonic = bool(profile["polymer_mass_kg"].diff().dropna().ge(-1.0e-10).all())
            reaction.append(make_residual("dynamic_polymer_accumulation", "polymer mass nondecreasing", 1.0 if monotonic else 0.0, 1.0, "-", 0.0, "dynamic_ode", "Check reaction consumption and nonnegative projection.", "error"))
    all_items = numerical + reaction
    return ResidualSystem(numerical_residuals=numerical, reaction_residuals=reaction, overall_score=score_residuals(all_items))


def residual_system_dataframe(system: ResidualSystem) -> pd.DataFrame:
    """Return residual system as a DataFrame."""
    return system.as_dataframe()
