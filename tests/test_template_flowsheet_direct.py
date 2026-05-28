from epdm_sim.flowsheet import run_flowsheet
from epdm_sim.template_config import TemplateProcessConfig
from epdm_sim.template_flowsheet import (
    run_epdm_flowsheet_adapter,
    run_template_flowsheet,
    template_flowsheet_dataframe,
    template_mass_balance,
    template_mass_balance_from_streams,
    template_stream_table,
    template_unit_table,
)


def test_template_flowsheet_direct_generic_and_epdm_paths():
    epdm = run_epdm_flowsheet_adapter()
    assert epdm.legacy_flowsheet is not None
    assert template_mass_balance(epdm)["feed_kg_h"] > 0
    generic = run_template_flowsheet(
        TemplateProcessConfig(
            template_id="generic_terpolymerization_apparent",
            monomer_feeds_kg_h={"monomer_A": 8, "monomer_B": 6, "monomer_C": 2},
            solvent_mass_kg_h=80,
        )
    )
    assert generic.application_kpis["polymer_kg_h"] > 0
    assert abs(sum(generic.application_kpis["segment_composition_wt"].values()) - 100) < 1e-9
    assert not template_stream_table(generic).empty
    assert not template_unit_table(generic).empty
    assert not template_flowsheet_dataframe(generic).empty
    streams = list(generic.streams.values())
    assert abs(template_mass_balance_from_streams(streams[0], generic.streams["Template polymer product"], generic.streams["Template flash vapor"])) < 1e-6
    assert run_flowsheet().kpis["template_adapter_used"] is True
