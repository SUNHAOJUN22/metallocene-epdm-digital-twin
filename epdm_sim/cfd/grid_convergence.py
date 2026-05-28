"""CFD scalar-label and grid-convergence diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from ..reaction_templates import template_with_fallback
from .mesh import CFDGeometryConfig
from .simple_solver import CFDInput, run_simple_cfd


@dataclass
class CFDGridConvergenceResult:
    """Grid-convergence metrics for selected CFD mesh sizes."""

    template_id: str
    metrics: pd.DataFrame
    scalar_labels: list[str]
    convergence_score: float
    warnings: list[str]

    def as_dataframe(self) -> pd.DataFrame:
        df = self.metrics.copy()
        df["template_id"] = self.template_id
        df["convergence_score"] = self.convergence_score
        df["scalar_labels"] = ", ".join(self.scalar_labels)
        return df


def scalar_labels_from_template(template_id: str = "EPDM_EPM_metallocene_solution") -> list[str]:
    """Return CFD scalar labels from reaction-template monomers."""
    template, warnings = template_with_fallback(template_id)
    labels = [f"C_{monomer}" for monomer in template.monomers]
    if "hydrogen" in template.chain_transfer_agents:
        labels.append("C_hydrogen")
    return labels + ["temperature", "viscosity", "fouling_index"]


def run_cfd_grid_convergence(
    base_input: CFDInput | None = None,
    template_id: str = "EPDM_EPM_metallocene_solution",
    grids: list[tuple[int, int]] | None = None,
) -> CFDGridConvergenceResult:
    """Run a lightweight grid convergence sweep."""
    base_input = base_input or CFDInput()
    grids = grids or [(40, 20), (80, 40)]
    rows = []
    warnings: list[str] = []
    previous = None
    diffs = []
    for nx, ny in grids:
        geometry = base_input.geometry.model_copy(update={"nx": nx, "ny": ny}) if hasattr(base_input.geometry, "model_copy") else base_input.geometry.copy(update={"nx": nx, "ny": ny})
        cfg = base_input.model_copy(update={"geometry": geometry}) if hasattr(base_input, "model_copy") else base_input.copy(update={"geometry": geometry})
        result = run_simple_cfd(cfg)
        d = result.diagnostics
        row = {
            "nx": nx,
            "ny": ny,
            "max_T_C": d.max_temperature_C,
            "dead_zone_fraction": d.dead_zone_fraction,
            "wall_fouling_max": d.wall_max_fouling_risk,
            "pressure_drop_Pa": d.pressure_drop_Pa,
            "mixing_index": d.mixing_index,
            "high_fouling_zone_area_fraction": d.high_fouling_zone_area_fraction,
        }
        rows.append(row)
        if previous is not None:
            denom = max(abs(previous["max_T_C"]), 1.0)
            diffs.append(abs(row["max_T_C"] - previous["max_T_C"]) / denom)
        previous = row
        warnings.extend(result.warnings)
    score = max(0.0, min(100.0, 100.0 * (1.0 - (max(diffs) if diffs else 0.0))))
    return CFDGridConvergenceResult(template_id, pd.DataFrame(rows), scalar_labels_from_template(template_id), score, warnings)

