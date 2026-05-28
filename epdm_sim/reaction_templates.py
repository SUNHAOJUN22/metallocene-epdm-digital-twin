"""Reaction template metadata for extensible polymerization models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from .utils import data_path, load_json


@dataclass(frozen=True)
class ReactionTemplate:
    """A reusable apparent polymerization reaction template."""

    template_id: str
    monomers: list[str]
    polymer_segments: dict[str, str]
    molecular_weights: dict[str, float]
    rate_law: str
    heat_of_polymerization: dict[str, float]
    chain_transfer_agents: list[str] = field(default_factory=list)
    catalyst_family: str = ""
    property_model: str | dict[str, Any] = ""
    validity_range: dict[str, str] = field(default_factory=dict)


def load_reaction_templates(path: str | None = None) -> dict[str, ReactionTemplate]:
    """Load reaction templates from local JSON."""
    payload = load_json(data_path("reaction_templates.json") if path is None else path)
    return {item["template_id"]: ReactionTemplate(**item) for item in payload.get("templates", [])}


def get_reaction_template(template_id: str = "EPDM_EPM_metallocene_solution") -> ReactionTemplate:
    """Return one reaction template by id."""
    templates = load_reaction_templates()
    if template_id not in templates:
        raise KeyError(f"Unknown reaction template: {template_id}")
    return templates[template_id]


def default_epdm_template() -> ReactionTemplate:
    """Return the default EPDM/EPM metallocene solution template."""
    return get_reaction_template("EPDM_EPM_metallocene_solution")


def segment_map_from_template(template_id: str = "EPDM_EPM_metallocene_solution") -> dict[str, str]:
    """Return monomer-to-polymer-segment mapping."""
    return dict(get_reaction_template(template_id).polymer_segments)


def monomers_from_template(template_id: str = "EPDM_EPM_metallocene_solution") -> tuple[str, ...]:
    """Return monomer names from a reaction template."""
    return tuple(get_reaction_template(template_id).monomers)


def molecular_weights_from_template(template_id: str = "EPDM_EPM_metallocene_solution") -> dict[str, float]:
    """Return monomer molecular weights in g/mol from a reaction template."""
    return dict(get_reaction_template(template_id).molecular_weights)


def template_with_fallback(template_id: str = "EPDM_EPM_metallocene_solution") -> tuple[ReactionTemplate, list[str]]:
    """Return a template and warnings, falling back to the default EPDM template."""
    try:
        return get_reaction_template(template_id), []
    except KeyError:
        return default_epdm_template(), [f"Unknown reaction template {template_id}; using EPDM_EPM_metallocene_solution."]


def heat_balance_deltaH_from_template(template_id: str = "EPDM_EPM_metallocene_solution") -> dict[str, float]:
    """Return default polymerization heats in kJ/mol."""
    return dict(get_reaction_template(template_id).heat_of_polymerization)


def property_model_from_template(template_id: str = "EPDM_EPM_metallocene_solution") -> dict[str, Any]:
    """Return a normalized property-model dispatch dictionary."""
    model = get_reaction_template(template_id).property_model
    if isinstance(model, dict):
        return dict(model)
    return {
        "model_id": str(model or "generic_solution_polymer_v1"),
        "composition_basis": "wt_percent_segments",
        "molecular_weight_model": "generic_positive_mw",
        "viscosity_model": "generic_viscosity_proxy",
        "thermal_model": "weighted_segment_tg",
        "crystallization_model": "none",
        "mooney_model": "generic_positive_proxy",
    }


def templates_dataframe(templates: dict[str, ReactionTemplate] | None = None) -> pd.DataFrame:
    """Return reaction templates as a report table."""
    templates = load_reaction_templates() if templates is None else templates
    rows: list[dict[str, Any]] = []
    for template in templates.values():
        rows.append(
            {
                "template_id": template.template_id,
                "monomers": ", ".join(template.monomers),
                "segments": str(template.polymer_segments),
                "rate_law": template.rate_law,
                "heat_of_polymerization_kJ_mol": str(template.heat_of_polymerization),
                "chain_transfer_agents": ", ".join(template.chain_transfer_agents),
                "catalyst_family": template.catalyst_family,
                "property_model": str(template.property_model),
                "validity_range": str(template.validity_range),
            }
        )
    return pd.DataFrame(rows)
