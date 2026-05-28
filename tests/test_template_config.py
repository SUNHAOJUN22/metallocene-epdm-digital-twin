from epdm_sim.flowsheet import ProcessConfig
from epdm_sim.template_config import (
    TemplateProcessConfig,
    epdm_feed_aliases,
    process_config_to_template_config,
    template_config_to_process_config,
)


def test_epdm_process_config_roundtrip_preserves_feeds():
    cfg = ProcessConfig(ethylene_kg_h=21.0, propylene_kg_h=31.0, enb_kg_h=4.0, hydrogen_g_h=6.0)
    template_cfg = process_config_to_template_config(cfg)
    assert template_cfg.monomer_feeds_kg_h["ethylene"] == 21.0
    assert template_cfg.monomer_feeds_kg_h["propylene"] == 31.0
    assert template_cfg.monomer_feeds_kg_h["ENB"] == 4.0
    assert template_cfg.chain_transfer_feeds["hydrogen"] == 6.0
    roundtrip = template_config_to_process_config(template_cfg)
    assert roundtrip.ethylene_kg_h == cfg.ethylene_kg_h
    assert roundtrip.enb_kg_h == cfg.enb_kg_h
    assert roundtrip.hydrogen_g_h == cfg.hydrogen_g_h


def test_generic_template_config_does_not_require_enb():
    cfg = TemplateProcessConfig(
        template_id="generic_solution_copolymerization",
        monomer_feeds_kg_h={"monomer_A": 1.0, "monomer_B": 2.0},
    )
    aliases = epdm_feed_aliases(cfg)
    assert aliases["enb_kg_h"] == 0.0
    assert cfg.monomer_feeds_kg_h["monomer_A"] > 0

