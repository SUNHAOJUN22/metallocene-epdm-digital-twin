from epdm_sim.heat_balance import HeatBalanceConfig, calculate_heat_balance, calculate_reaction_heat


def test_reaction_heat_is_positive_for_negative_delta_h():
    q = calculate_reaction_heat({"ethylene": 10.0, "propylene": 5.0, "ENB": 1.0})
    assert q == 10.0 * 95.0 + 5.0 * 85.0 + 1.0 * 80.0


def test_heat_balance_reports_margin_and_risk():
    result = calculate_heat_balance(
        {"ethylene": 100.0, "propylene": 0.0, "ENB": 0.0},
        mass_holdup_kg=100.0,
        Cp_mix_kJ_kgK=2.0,
        config=HeatBalanceConfig(overall_U_W_m2K=300.0, heat_transfer_area_m2=2.0),
    )
    assert result.Q_rxn_kW > 0.0
    assert result.deltaT_ad_K > 0.0
    assert result.thermal_risk in {"low", "medium", "high"}
