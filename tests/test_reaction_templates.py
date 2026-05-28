from epdm_sim.reaction_templates import (
    default_epdm_template,
    heat_balance_deltaH_from_template,
    load_reaction_templates,
    segment_map_from_template,
    templates_dataframe,
)


def test_reaction_templates_load():
    templates = load_reaction_templates()
    assert "EPDM_EPM_metallocene_solution" in templates
    assert not templates_dataframe(templates).empty


def test_default_epdm_template_contains_epdm_monomers():
    template = default_epdm_template()
    assert {"ethylene", "propylene", "ENB"}.issubset(set(template.monomers))
    assert segment_map_from_template()["ethylene"] == "E"


def test_template_heat_of_polymerization_negative():
    delta_h = heat_balance_deltaH_from_template()
    assert delta_h["ethylene"] < 0
    assert delta_h["propylene"] < 0
    assert delta_h["ENB"] < 0
