"""Reactor material-balance helpers."""

from __future__ import annotations

from ..reaction_templates import get_reaction_template


def consumed_monomer_mass_kg_h(template_id: str, consumed_moles_h: dict[str, float]) -> float:
    """Return total consumed monomer mass in kg/h."""
    template = get_reaction_template(template_id)
    return sum(max(float(mol_h), 0.0) * float(template.molecular_weights.get(monomer, 100.0)) / 1000.0 for monomer, mol_h in consumed_moles_h.items())

