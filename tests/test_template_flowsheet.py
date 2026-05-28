from epdm_sim.flowsheet import load_default_config, run_flowsheet
from epdm_sim.template_config import TemplateProcessConfig, process_config_to_template_config
from epdm_sim.template_flowsheet import run_template_flowsheet, template_mass_balance


def test_epdm_template_flowsheet_matches_legacy_order():
    cfg = load_default_config()
    legacy = run_flowsheet(cfg)
    template_result = run_template_flowsheet(process_config_to_template_config(cfg))
    assert template_result.application_kpis["polymer_kg_h"] > 0
    ratio = template_result.application_kpis["polymer_kg_h"] / legacy.kpis["polymer_kg_h"]
    assert 0.95 <= ratio <= 1.05
    assert any(kpi.compatibility_alias == "C2_wt" for kpi in template_result.template_kpis)
    assert legacy.kpis["template_adapter_used"] is True
    assert legacy.kpis["template_id"] == "EPDM_EPM_metallocene_solution"


def test_generic_template_flowsheet_runs_and_closes():
    cfg = TemplateProcessConfig(
        template_id="generic_terpolymerization_apparent",
        monomer_feeds_kg_h={"monomer_A": 2.0, "monomer_B": 3.0, "monomer_C": 1.0},
        solvent_mass_kg_h=20.0,
    )
    result = run_template_flowsheet(cfg)
    assert result.application_kpis["polymer_kg_h"] >= 0
    assert abs(template_mass_balance(result)["closure_error_pct"]) < 1.0e-6
    comp_sum = sum(result.application_kpis["segment_composition_wt"].values())
    assert abs(comp_sum - 100.0) < 1.0e-6 if comp_sum > 0 else True
