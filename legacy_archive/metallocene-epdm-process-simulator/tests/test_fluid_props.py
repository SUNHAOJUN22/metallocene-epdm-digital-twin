from epdm_sim.flowsheet import load_default_config, run_flowsheet
from epdm_sim.fluid_props import calculate_pipe_hydraulics


def test_fluid_properties_are_positive():
    result = run_flowsheet(load_default_config())
    props = result.fluid_properties
    assert props.liquid_density_kg_m3 > 0.0
    assert props.Cp_liq_kJ_kgK > 0.0
    assert props.dynamic_viscosity_Pa_s > 0.0
    assert props.kinematic_viscosity_m2_s > 0.0
    assert props.fouling_risk in {"low", "medium", "high"}


def test_pipe_hydraulics_pressure_drop_positive():
    hydraulics = calculate_pipe_hydraulics(
        liquid_density_kg_m3=700.0,
        dynamic_viscosity_Pa_s=0.001,
        volumetric_flow_m3_h=1.0,
        pipe_length_m=10.0,
        pipe_diameter_m=0.02,
    )
    assert hydraulics.Reynolds > 0.0
    assert hydraulics.pressure_drop_kPa >= 0.0
    assert hydraulics.flow_regime in {"laminar", "turbulent"}
