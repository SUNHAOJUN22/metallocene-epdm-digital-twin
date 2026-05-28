"""State scaling helpers and BDF readiness diagnostics for template ODEs."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from .state_vector import build_state_layout_from_template
from .utils import positive


@dataclass(frozen=True)
class BDFReadiness:
    """BDF readiness diagnostic."""

    ready: bool
    fallback_recommended: bool
    reason: str
    min_scale: float
    max_scale: float

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _as_array(values: Any) -> np.ndarray:
    return np.asarray(values, dtype=float)


def scale_state_vector(y: Any, scales: Any) -> np.ndarray:
    """Scale an ODE state vector by positive characteristic scales."""
    arr = _as_array(y)
    scale = np.maximum(_as_array(scales), 1.0e-30)
    if arr.shape != scale.shape:
        raise ValueError("state vector and scales must have the same shape")
    return arr / scale


def unscale_state_vector(y_scaled: Any, scales: Any) -> np.ndarray:
    """Reverse scale_state_vector."""
    arr = _as_array(y_scaled)
    scale = np.maximum(_as_array(scales), 1.0e-30)
    if arr.shape != scale.shape:
        raise ValueError("scaled state vector and scales must have the same shape")
    return arr * scale


def estimate_state_scales(template_id: str, config: Any | None = None) -> dict[str, float]:
    """Estimate positive characteristic scales for a template state layout."""
    layout = build_state_layout_from_template(template_id)
    pressure = positive(getattr(config, "pressure_MPa", 1.0)) * 1.0e6 if config is not None else 1.0e6
    temperature = positive(getattr(config, "temperature_C", 100.0) + 273.15, 1.0) if config is not None else 373.15
    polymer_scale = max(positive(getattr(config, "solvent_mass_kg_h", 100.0)) * positive(getattr(config, "residence_time_min", 30.0)) / 60.0 * 0.2, 1.0)
    # Refined catalyst scale: standard umol feed ranges from 0.1 to 1000. 
    # Use 1e-6 as baseline if umol_h is not provided.
    cat_umol = positive(getattr(config, "catalyst_umol_h", 100.0))
    cat_scale = max(cat_umol * 1.0e-6, 1.0e-8)
    
    scales: dict[str, float] = {}
    for label in layout.labels:
        if label.startswith("liquid_moles:"):
            scales[label] = 10.0
        elif label.startswith("gas_moles:"):
            scales[label] = 5.0
        elif label.startswith("segment_masses:"):
            scales[label] = polymer_scale
        elif label.startswith("chain_transfer_moles:"):
            scales[label] = 0.1
        elif label == "solvent_mass_kg":
            scales[label] = max(polymer_scale * 5.0, 1.0)
        elif label == "polymer_mass_kg":
            scales[label] = polymer_scale
        elif label == "T_K":
            scales[label] = temperature
        elif label == "P_Pa":
            scales[label] = pressure
        elif label == "catalyst_active_mol":
            scales[label] = cat_scale
        elif label == "time_min":
            scales[label] = max(positive(getattr(config, "residence_time_min", 30.0)) if config is not None else 30.0, 1.0)
        else:
            scales[label] = 1.0
    return scales


def bdf_readiness_check(config: Any | None = None, template_id: str = "EPDM_EPM_metallocene_solution") -> BDFReadiness:
    """Return whether the current MVP should attempt BDF or fallback."""
    scales = np.asarray(list(estimate_state_scales(template_id, config).values()), dtype=float)
    finite = bool(np.isfinite(scales).all() and np.all(scales > 0.0))
    ratio = float(scales.max() / max(scales.min(), 1.0e-30)) if finite else float("inf")
    if not finite:
        return BDFReadiness(False, True, "non-finite or non-positive state scale", 0.0, float("inf"))
    # Relaxing threshold to 1e12 to allow Pressure (1e6) vs Catalyst (1e-6) scaling
    if ratio > 1.0e12:
        return BDFReadiness(False, True, f"state scales span {ratio:.2e}; extreme stiffness requires explicit_bounded fallback", float(scales.min()), float(scales.max()))
    return BDFReadiness(True, False, "state scales finite and bounded; BDF enabled for production precision", float(scales.min()), float(scales.max()))
