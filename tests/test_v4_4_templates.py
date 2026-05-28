from epdm_sim.conservation import segment_balance
from epdm_sim.flowsheet import build_feed_stream, load_default_config
from epdm_sim.heat_balance import HeatBalanceConfig
from epdm_sim.reaction_templates import default_epdm_template, heat_balance_deltaH_from_template, template_with_fallback
from epdm_sim.reactor import MONOMERS, SEGMENT_MAP, simulate_reactor
from epdm_sim.utils import c_to_k


def test_default_template_matches_epdm_runtime_constants():
    template = default_epdm_template()
    assert tuple(template.monomers) == MONOMERS
    assert template.polymer_segments == SEGMENT_MAP


def test_reactor_reads_default_template_without_changing_behavior():
    cfg = load_default_config()
    feed = build_feed_stream(cfg)
    result = simulate_reactor(feed, c_to_k(cfg.temperature_C), cfg.pressure_MPa, cfg.residence_time_min, cfg.reactor_volume_L, cfg.catalyst_umol_h, cfg.AlTi_ratio, cfg.BHT_ratio)
    assert set(result.consumed_mol_h) == set(default_epdm_template().monomers)
    assert segment_balance(result).passed


def test_heat_balance_defaults_from_template():
    assert HeatBalanceConfig().deltaH_polymerization == heat_balance_deltaH_from_template()


def test_unknown_template_falls_back_with_warning():
    template, warnings = template_with_fallback("missing-template")
    assert template.template_id == "EPDM_EPM_metallocene_solution"
    assert warnings


def test_generic_templates_load_without_epdm_execution():
    from epdm_sim.reaction_templates import get_reaction_template

    template = get_reaction_template("generic_solution_copolymerization")
    assert template.monomers == ["monomer_A", "monomer_B"]
