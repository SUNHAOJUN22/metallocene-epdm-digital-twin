from epdm_sim.flowsheet import run_flowsheet
from epdm_sim.kpi_adapter import build_template_kpis, epdm_compatibility_kpis
from epdm_sim.kpi_schema import kpis_to_dataframe


def test_template_kpis_keep_epdm_compatibility_aliases():
    result = run_flowsheet()
    rows = build_template_kpis("EPDM_EPM_metallocene_solution", result)
    aliases = epdm_compatibility_kpis(rows)
    assert "C2_wt" in aliases
    assert "ENB_conversion_pct" in aliases
    comp = aliases["C2_wt"] + aliases["C3_wt"] + aliases["ENB_wt"]
    assert abs(comp - 100.0) < 1e-6
    assert not kpis_to_dataframe(rows).empty
