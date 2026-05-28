"""Iterative recycle tear-stream solver for simplified EPDM flowsheets."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

import pandas as pd

from .utils import clamp, positive


RECYCLE_COMPONENTS = ("ethylene", "propylene", "hydrogen", "ENB", "hexane", "heptane", "toluene")


@dataclass
class RecycleSolverResult:
    """Result from a fixed-point recycle calculation."""

    recycle_flow_kg_h: dict[str, float]
    fresh_feed_requirement_kg_h: dict[str, float]
    purge_loss_kg_h: dict[str, float]
    convergence_iterations: int
    closure_error: float
    monomer_recovery_pct: float
    solvent_recovery_pct: float
    history: pd.DataFrame = field(default_factory=pd.DataFrame)

    def as_dataframe(self) -> pd.DataFrame:
        """Return component-level recycle summary."""
        rows = []
        for comp in sorted(set(self.recycle_flow_kg_h) | set(self.fresh_feed_requirement_kg_h) | set(self.purge_loss_kg_h)):
            rows.append(
                {
                    "component": comp,
                    "recycle_kg_h": self.recycle_flow_kg_h.get(comp, 0.0),
                    "fresh_makeup_kg_h": self.fresh_feed_requirement_kg_h.get(comp, 0.0),
                    "purge_loss_kg_h": self.purge_loss_kg_h.get(comp, 0.0),
                }
            )
        return pd.DataFrame(rows)


def solve_recycle(
    flash1_vapor_kg_h: Mapping[str, float],
    flash2_vapor_kg_h: Mapping[str, float],
    fresh_feed_kg_h: Mapping[str, float],
    purge_fraction: float = 0.05,
    *,
    max_iter: int = 50,
    tol: float = 1.0e-6,
    relaxation: float = 0.55,
) -> RecycleSolverResult:
    """Solve recycle loops using Wegstein-accelerated fixed-point iteration."""
    purge = min(max(float(purge_fraction), 0.0), 1.0)
    recovered = {
        comp: positive(flash1_vapor_kg_h.get(comp, 0.0)) + positive(flash2_vapor_kg_h.get(comp, 0.0))
        for comp in RECYCLE_COMPONENTS
    }
    
    # State tracking for Wegstein
    x_prev = {comp: 0.0 for comp in RECYCLE_COMPONENTS}
    f_prev = {comp: (1.0 - purge) * recovered.get(comp, 0.0) for comp in RECYCLE_COMPONENTS}
    x_curr = f_prev.copy()
    
    rows = []
    closure = 1.0
    
    for iteration in range(1, max_iter + 1):
        # Calculate function value f(x_curr)
        f_curr = {comp: (1.0 - purge) * recovered.get(comp, 0.0) for comp in RECYCLE_COMPONENTS}
        
        # Calculate Wegstein q-factor for each component
        new_x = {}
        for comp in RECYCLE_COMPONENTS:
            dx = x_curr[comp] - x_prev[comp]
            df = f_curr[comp] - f_prev[comp]
            
            if abs(dx) > 1e-9:
                s = df / dx
                q = s / (s - 1.0) if abs(s - 1.0) > 1e-4 else relaxation
                # Safety bound for q
                q = clamp(q, -2.0, 0.85)
            else:
                q = relaxation
                
            new_x[comp] = q * x_curr[comp] + (1.0 - q) * f_curr[comp]
            
        closure = max(abs(new_x[comp] - x_curr[comp]) for comp in RECYCLE_COMPONENTS)
        
        # Update history
        x_prev = x_curr
        f_prev = f_curr
        x_curr = new_x
        
        rows.append({"iteration": iteration, "closure_error": closure, "total_recycle_kg_h": sum(x_curr.values())})
        if closure < tol:
            break
            
    recycle = x_curr
    purge_loss = {comp: purge * recovered.get(comp, 0.0) for comp in RECYCLE_COMPONENTS}
    fresh = {
        comp: max(positive(fresh_feed_kg_h.get(comp, 0.0)) - recycle.get(comp, 0.0), 0.0)
        for comp in sorted(set(fresh_feed_kg_h) | set(RECYCLE_COMPONENTS))
    }
    monomer_in = sum(recovered.get(comp, 0.0) for comp in ["ethylene", "propylene", "hydrogen"])
    monomer_recycle = sum(recycle.get(comp, 0.0) for comp in ["ethylene", "propylene", "hydrogen"])
    solvent_in = sum(recovered.get(comp, 0.0) for comp in ["hexane", "heptane", "toluene", "ENB"])
    solvent_recycle = sum(recycle.get(comp, 0.0) for comp in ["hexane", "heptane", "toluene", "ENB"])
    return RecycleSolverResult(
        recycle_flow_kg_h=recycle,
        fresh_feed_requirement_kg_h=fresh,
        purge_loss_kg_h=purge_loss,
        convergence_iterations=len(rows),
        closure_error=closure,
        monomer_recovery_pct=100.0 * monomer_recycle / monomer_in if monomer_in > 0 else 0.0,
        solvent_recovery_pct=100.0 * solvent_recycle / solvent_in if solvent_in > 0 else 0.0,
        history=pd.DataFrame(rows),
    )
