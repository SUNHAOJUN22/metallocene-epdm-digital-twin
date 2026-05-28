from epdm_sim.feed_adapter import build_template_feed_stream, validate_template_feed_map
from epdm_sim.template_config import TemplateProcessConfig


def test_template_feed_stream_handles_generic_monomers():
    cfg = TemplateProcessConfig(
        template_id="generic_terpolymerization_apparent",
        monomer_feeds_kg_h={"monomer_A": 1.0, "monomer_B": 1.5, "monomer_C": 0.5},
    )
    stream = build_template_feed_stream(cfg)
    assert stream.total_mass_flow() > 0
    assert stream.molar_flows["monomer_A"] > 0
    assert stream.molar_flows["monomer_C"] > 0


def test_template_feed_validation_rejects_unknown_and_negative():
    cfg = TemplateProcessConfig(
        template_id="generic_solution_copolymerization",
        monomer_feeds_kg_h={"monomer_A": 1.0, "unknown": 2.0, "monomer_B": -1.0},
    )
    checks = validate_template_feed_map(cfg)
    errors = [check for check in checks if check.severity == "error"]
    assert len(errors) >= 2

