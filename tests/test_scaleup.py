from epdm_sim.scaleup import ScaleUpCase, calculate_scaleup_case, compare_scaleup, power_number


def test_scaleup_metrics_are_positive():
    result = calculate_scaleup_case(
        ScaleUpCase(name="5L", volume_L=5.0, rpm=500.0, impeller_diameter_m=0.08, viscosity_Pa_s=0.004)
    )
    assert result.power_per_volume_kW_m3 > 0.0
    assert result.impeller_Re > 0.0
    assert result.tip_speed_m_s > 0.0
    assert result.mixing_time_s > 0.0


def test_scaleup_compare_contains_2l_5l_custom():
    df = compare_scaleup(700.0, 0.003, custom_volume_L=20.0)
    assert list(df["case"]) == ["2L reference", "5L pilot", "custom"]
    assert (df["recommended_rpm"] > 0.0).all()


def test_power_number_decreases_from_laminar_to_turbulent():
    assert power_number("pitched blade turbine", 5.0) > power_number("pitched blade turbine", 20000.0)
