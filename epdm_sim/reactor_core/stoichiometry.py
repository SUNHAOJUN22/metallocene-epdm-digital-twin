"""Stoichiometry helpers for template polymerization."""

from __future__ import annotations

from ..reaction_templates import get_reaction_template


def monomer_segment_map(template_id: str = "EPDM_EPM_metallocene_solution") -> dict[str, str]:
    """Return template monomer-to-segment stoichiometry map."""
    template = get_reaction_template(template_id)
    return dict(template.polymer_segments)

