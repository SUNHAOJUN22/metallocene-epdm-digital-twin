"""RHS term diagnostics coupled to template ODE state derivatives."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd

from ..state_vector import StateVectorLayout, unpack_state
from ..template_ode_rhs import TemplateODERHSContext, template_ode_rhs


@dataclass(frozen=True)
class RHSTerm:
    """One physically labelled RHS contribution."""

    term_id: str
    affected_state: str
    value: float
    unit: str
    sign_convention: str
    physical_meaning: str
    source_equation_id: str
    residual_id: str
    finite_check: bool
    nonnegative_check: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _term_for_label(label: str, value: float) -> RHSTerm:
    if label.startswith("liquid_moles:"):
        term_id = "monomer_liquid_accumulation"
        unit = "mol/min"
        meaning = "feed + gas-liquid transfer - reaction consumption"
        equation = "ode_accumulation"
        residual = "dynamic_monomer_accumulation"
    elif label.startswith("gas_moles:"):
        term_id = "gas_inventory_accumulation"
        unit = "mol/min"
        meaning = "pressure-control feed and gas-liquid transfer"
        equation = "gas_liquid_inventory"
        residual = "dynamic_gas_inventory"
    elif label.startswith("segment_masses:"):
        term_id = "polymer_segment_generation"
        unit = "kg/min"
        meaning = "monomer consumption generates polymer segment mass"
        equation = "monomer_to_polymer_mass"
        residual = "dynamic_segment_generation"
    elif label.startswith("chain_transfer_moles:"):
        term_id = "chain_transfer_inventory"
        unit = "mol/min"
        meaning = "chain-transfer feed and gas-liquid transfer"
        equation = "chain_transfer_balance"
        residual = "dynamic_chain_transfer"
    elif label == "T_K":
        term_id = "energy_accumulation"
        unit = "K/min"
        meaning = "heat generation minus heat removal divided by heat capacity"
        equation = "dynamic_energy_balance"
        residual = "dynamic_energy_accumulation"
    elif label == "P_Pa":
        term_id = "pressure_control"
        unit = "Pa/min"
        meaning = "gas inventory response to pressure-control feed"
        equation = "pressure_control_balance"
        residual = "dynamic_pressure_control"
    elif label == "catalyst_active_mol":
        term_id = "catalyst_decay_or_quench"
        unit = "mol/min"
        meaning = "catalyst decay and quench deactivation"
        equation = "catalyst_deactivation"
        residual = "dynamic_catalyst_decay"
    elif label == "polymer_mass_kg":
        term_id = "polymer_mass_generation"
        unit = "kg/min"
        meaning = "sum of generated polymer segment masses"
        equation = "polymer_segment_sum"
        residual = "dynamic_polymer_mass"
    else:
        term_id = "state_accumulation"
        unit = "state/min"
        meaning = "state derivative from template ODE RHS"
        equation = "ode_accumulation"
        residual = "dynamic_numerical"
    finite = bool(np.isfinite(float(value)))
    nonnegative = True if term_id not in {"polymer_mass_generation", "polymer_segment_generation"} else float(value) >= -1.0e-12
    return RHSTerm(term_id, label, float(value), unit, "positive increases affected state", meaning, equation, residual, finite, nonnegative)


def rhs_terms_for_state(t_min: float, y: np.ndarray, context: TemplateODERHSContext) -> pd.DataFrame:
    """Return labelled RHS derivative terms for one state vector."""
    dy = template_ode_rhs(float(t_min), y, context)
    return pd.DataFrame([_term_for_label(label, value).as_dict() for label, value in zip(context.layout.labels, dy)])


def rhs_term_schema() -> pd.DataFrame:
    """Return the expected RHS term schema without running a model."""
    labels = [
        "feed_term",
        "reaction_consumption",
        "gas_liquid_transfer",
        "pressure_control",
        "heat_generation",
        "heat_removal",
        "catalyst_decay",
        "quench_term",
    ]
    return pd.DataFrame(
        {
            "term_id": labels,
            "required_fields": "value; unit; affected_state; physical_meaning; source_equation_id; residual_id",
            "gate": "RHS-residual coupling",
        }
    )


def rhs_terms_from_profile(dynamic_result: Any) -> pd.DataFrame:
    """Return a lightweight RHS-coupling table from an existing profile."""
    profile = getattr(dynamic_result, "profile", pd.DataFrame())
    if profile is None or profile.empty:
        return pd.DataFrame([{"term_id": "profile_missing", "passed": False, "reason": "dynamic profile not supplied"}])
    rows: list[dict[str, Any]] = []
    rate_cols = [col for col in profile.columns if col.startswith("r_") and col.endswith("_mol_h")]
    final_rates = float(profile[rate_cols].iloc[-1].abs().sum()) if rate_cols else 0.0
    rows.append({"term_id": "reaction_consumption", "residual_id": "dynamic_monomer_accumulation", "value": final_rates, "unit": "mol/h", "passed": np.isfinite(final_rates)})
    if "Q_rxn_kW" in profile:
        q_min = float(profile["Q_rxn_kW"].min())
        rows.append({"term_id": "heat_generation", "residual_id": "dynamic_energy_accumulation", "value": q_min, "unit": "kW", "passed": np.isfinite(q_min) and q_min >= -1.0e-12})
    if "catalyst_active_mol" in profile:
        cat_final = float(profile["catalyst_active_mol"].iloc[-1])
        rows.append({"term_id": "catalyst_decay", "residual_id": "dynamic_catalyst_decay", "value": cat_final, "unit": "mol", "passed": np.isfinite(cat_final) and cat_final >= -1.0e-12})
    return pd.DataFrame(rows)

