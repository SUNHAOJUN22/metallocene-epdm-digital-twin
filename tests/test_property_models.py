from epdm_sim.property_models import predict_polymer_properties, property_models_dataframe


def test_epdm_property_model_positive_and_compatible():
    result = predict_polymer_properties(
        "EPDM_EPM_metallocene_solution",
        {"ethylene": 54.3, "propylene": 38.9, "ENB": 6.8},
        360300,
        3.39,
        {"temperature_K": 373.15, "solids_wt": 12.0},
    )
    assert result.Mooney > 0
    assert result.Mw == 360300
    assert result.PDI >= 1
    assert result.Tg_C < 50
    assert result.fouling_index >= 0


def test_generic_property_model_does_not_require_enb():
    result = predict_polymer_properties(
        "generic_solution_copolymerization",
        {"monomer_A": 60.0, "monomer_B": 40.0},
        250000,
        2.5,
        {"temperature_K": 360.0, "solids_wt": 8.0},
    )
    assert result.Mooney > 0
    assert result.Tg_C == result.Tg_C
    assert result.Tm_C is None
    assert result.warnings


def test_property_model_normalizes_composition_and_clips_pdi():
    result = predict_polymer_properties(
        "EPDM_EPM_metallocene_solution",
        {"ethylene": 50.0, "propylene": 30.0, "ENB": 5.0},
        200000,
        0.8,
    )
    assert abs(sum(result.composition_wt.values()) - 100.0) < 1.0e-9
    assert result.PDI >= 1.0
    assert result.warnings


def test_property_models_dataframe_contains_templates():
    df = property_models_dataframe()
    assert "template_id" in df
    assert "model_id" in df
    assert not df.empty
