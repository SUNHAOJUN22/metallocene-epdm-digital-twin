"""Template-driven dynamic reactor state-vector utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from .reaction_templates import template_with_fallback
from .utils import positive


@dataclass(frozen=True)
class StateVectorLayout:
    """Ordered state-vector layout generated from a reaction template."""

    template_id: str
    liquid_moles: list[str]
    gas_moles: list[str]
    segment_masses: list[str]
    chain_transfer_moles: list[str]
    scalar_fields: list[str] = field(
        default_factory=lambda: ["solvent_mass_kg", "polymer_mass_kg", "T_K", "P_Pa", "catalyst_active_mol", "time_min"]
    )
    warnings: list[str] = field(default_factory=list)

    @property
    def labels(self) -> list[str]:
        """Return ordered flat vector labels."""
        labels = [f"liquid_moles:{name}" for name in self.liquid_moles]
        labels.extend(f"gas_moles:{name}" for name in self.gas_moles)
        labels.extend(f"segment_masses:{name}" for name in self.segment_masses)
        labels.extend(f"chain_transfer_moles:{name}" for name in self.chain_transfer_moles)
        labels.extend(self.scalar_fields)
        return labels

    def as_dataframe(self) -> pd.DataFrame:
        """Return layout labels as a report table."""
        return pd.DataFrame({"index": range(len(self.labels)), "state_label": self.labels, "template_id": self.template_id})


def build_state_layout_from_template(template_id: str = "EPDM_EPM_metallocene_solution") -> StateVectorLayout:
    """Build an ordered dynamic state layout from a reaction template."""
    template, warnings = template_with_fallback(template_id)
    segments = list(dict.fromkeys(template.polymer_segments.get(monomer, monomer) for monomer in template.monomers))
    gas_components = list(dict.fromkeys([*template.monomers, *template.chain_transfer_agents]))
    return StateVectorLayout(
        template_id=template.template_id,
        liquid_moles=list(template.monomers),
        gas_moles=gas_components,
        segment_masses=segments,
        chain_transfer_moles=list(template.chain_transfer_agents),
        warnings=warnings,
    )


def default_state_dict(layout: StateVectorLayout) -> dict[str, Any]:
    """Return a nested zero state with physically meaningful defaults."""
    return {
        "liquid_moles": {name: 0.0 for name in layout.liquid_moles},
        "gas_moles": {name: 0.0 for name in layout.gas_moles},
        "segment_masses": {name: 0.0 for name in layout.segment_masses},
        "chain_transfer_moles": {name: 0.0 for name in layout.chain_transfer_moles},
        "solvent_mass_kg": 0.0,
        "polymer_mass_kg": 0.0,
        "T_K": 373.15,
        "P_Pa": 1.0e6,
        "catalyst_active_mol": 0.0,
        "time_min": 0.0,
    }


def pack_state(layout: StateVectorLayout, state: dict[str, Any]) -> np.ndarray:
    """Pack a nested state dictionary into a flat numpy vector."""
    values: list[float] = []
    for name in layout.liquid_moles:
        values.append(float(state.get("liquid_moles", {}).get(name, 0.0)))
    for name in layout.gas_moles:
        values.append(float(state.get("gas_moles", {}).get(name, 0.0)))
    for name in layout.segment_masses:
        values.append(float(state.get("segment_masses", {}).get(name, 0.0)))
    for name in layout.chain_transfer_moles:
        values.append(float(state.get("chain_transfer_moles", {}).get(name, 0.0)))
    for name in layout.scalar_fields:
        values.append(float(state.get(name, 0.0)))
    return np.asarray(values, dtype=float)


def unpack_state(layout: StateVectorLayout, y: list[float] | np.ndarray) -> dict[str, Any]:
    """Unpack a flat vector into a nested state dictionary."""
    arr = np.asarray(y, dtype=float).ravel()
    if len(arr) != len(layout.labels):
        raise ValueError(f"State vector length {len(arr)} does not match layout length {len(layout.labels)}.")
    idx = 0
    state = default_state_dict(layout)
    for name in layout.liquid_moles:
        state["liquid_moles"][name] = float(arr[idx]); idx += 1
    for name in layout.gas_moles:
        state["gas_moles"][name] = float(arr[idx]); idx += 1
    for name in layout.segment_masses:
        state["segment_masses"][name] = float(arr[idx]); idx += 1
    for name in layout.chain_transfer_moles:
        state["chain_transfer_moles"][name] = float(arr[idx]); idx += 1
    for name in layout.scalar_fields:
        state[name] = float(arr[idx]); idx += 1
    return state


def validate_state_nonnegative(state: dict[str, Any]) -> list[str]:
    """Return warnings for negative or non-finite state entries."""
    warnings: list[str] = []
    for group in ("liquid_moles", "gas_moles", "segment_masses", "chain_transfer_moles"):
        for name, value in (state.get(group, {}) or {}).items():
            if not np.isfinite(float(value)) or float(value) < -1.0e-10:
                warnings.append(f"{group}:{name} is negative or non-finite: {value}")
    for name in ("solvent_mass_kg", "polymer_mass_kg", "T_K", "P_Pa", "catalyst_active_mol"):
        value = float(state.get(name, 0.0))
        if not np.isfinite(value) or value < -1.0e-10:
            warnings.append(f"{name} is negative or non-finite: {value}")
    return warnings


def clamp_state_nonnegative(state: dict[str, Any]) -> dict[str, Any]:
    """Return a copy with extensive variables clipped to non-negative values."""
    clean = default_state_dict(build_state_layout_from_template())
    clean.update(state)
    for group in ("liquid_moles", "gas_moles", "segment_masses", "chain_transfer_moles"):
        clean[group] = {key: positive(value) for key, value in (state.get(group, {}) or {}).items()}
    for name in ("solvent_mass_kg", "polymer_mass_kg", "T_K", "P_Pa", "catalyst_active_mol", "time_min"):
        clean[name] = positive(state.get(name, 0.0))
    return clean
