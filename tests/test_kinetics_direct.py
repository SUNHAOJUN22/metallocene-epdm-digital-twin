from epdm_sim.kinetics import (
    KineticParameters,
    active_center_concentration,
    activation_factor,
    arrhenius,
    calculate_template_conversions,
    calculate_template_polymer_segments,
    calculate_template_rates,
    estimate_molecular_weight,
    ethylene_competition_factor,
    pressure_factor_enb,
    reaction_rates,
)


def test_kinetics_direct_scientific_trends():
    params = KineticParameters()
    assert arrhenius(1.0, 30000.0, 390.0) > arrhenius(1.0, 30000.0, 350.0)
    assert activation_factor(1000, 1.0, params) >= activation_factor(100, 0.0, params)
    assert active_center_concentration(100, 10, 1000, 0, 0.5, params) >= 0
    assert pressure_factor_enb(2.0, params) <= pressure_factor_enb(0.7, params)
    assert ethylene_competition_factor(1.0, 0.1, params) <= ethylene_competition_factor(0.1, 1.0, params)
    rates = reaction_rates({"ethylene": 0.5, "propylene": 0.3, "ENB": 0.05}, 1e-6, 373.15, 1.0, params)
    assert rates.r_E_mol_L_h >= 0 and rates.r_P_mol_L_h >= 0 and rates.r_ENB_mol_L_h >= 0
    template_rates = calculate_template_rates("generic_terpolymerization_apparent", {"monomer_A": 0.1}, 1e-6, {"temperature_K": 373.15}, params)
    assert all(value >= 0 for value in template_rates.rates_mol_L_h.values())
    conversions = calculate_template_conversions("EPDM_EPM_metallocene_solution", {"ethylene": 10}, {"ethylene": 20})
    assert conversions["ethylene"] == 1.0
    segments = calculate_template_polymer_segments("EPDM_EPM_metallocene_solution", {"ethylene": 10.0})
    assert sum(segments.values()) > 0
    assert estimate_molecular_weight(params.Mw0, 0.1, 55.0, 10.0, params) < estimate_molecular_weight(params.Mw0, 0.0, 55.0, 10.0, params)
