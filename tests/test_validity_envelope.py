from epdm_sim.flowsheet import ProcessConfig
from epdm_sim.validity_envelope import (
    check_value_against_range,
    property_source_validity_envelope,
    registry_validity_ranges,
    run_validity_envelope_for_config,
    template_validity_ranges,
    validity_envelope_dataframe,
    validity_score,
)


def test_validity_envelope_inside_near_edge_outside():
    inside = check_value_against_range("m", "temperature_C", 100.0, (60.0, 180.0))
    edge = check_value_against_range("m", "temperature_C", 62.0, (60.0, 180.0))
    outside = check_value_against_range("m", "temperature_C", 250.0, (60.0, 180.0))
    assert inside.status == "inside"
    assert edge.status == "near_edge"
    assert outside.status == "outside"
    assert validity_score([inside, edge, outside]) < 100


def test_validity_envelope_for_default_config_and_sources():
    results = run_validity_envelope_for_config(ProcessConfig())
    df = validity_envelope_dataframe(results)
    assert not df.empty
    assert "outside" not in set(df["status"])
    assert registry_validity_ranges("flowsheet")["temperature_C"][0] < 100
    assert template_validity_ranges("EPDM_EPM_metallocene_solution") is not None
    props = property_source_validity_envelope(100.0, 1.0)
    assert props is not None
