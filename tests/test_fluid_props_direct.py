import math

from epdm_sim.flowsheet import load_default_config, run_flowsheet
from epdm_sim.fluid_props import (
    apparent_viscosity,
    calculate_fluid_properties,
    calculate_pipe_hydraulics,
    estimate_stream_volumetric_flow_m3_h,
    fluid_fouling_risk,
    polymer_solution_viscosity,
)


def test_fluid_props_direct_trends_and_bounds():
    result = run_flowsheet(load_default_config())
    stream = result.streams["Flash-1 liquid"]
    mu_low_solids = polymer_solution_viscosity(stream, 373.15, 300000.0, solids_wt_override=5.0)
    mu_high_solids = polymer_solution_viscosity(stream, 373.15, 300000.0, solids_wt_override=25.0)
    mu_hot = polymer_solution_viscosity(stream, 403.15, 300000.0, solids_wt_override=15.0)
    mu_cold = polymer_solution_viscosity(stream, 353.15, 300000.0, solids_wt_override=15.0)
    assert mu_high_solids > mu_low_solids > 0
    assert mu_hot < mu_cold
    assert apparent_viscosity(1.0, 100.0, "power_law") <= apparent_viscosity(1.0, 1.0, "power_law")

    props = calculate_fluid_properties(stream, result.kpis["Mw"])
    assert props.liquid_density_kg_m3 > 0
    assert props.Cp_liq_kJ_kgK > 0
    assert props.dynamic_viscosity_Pa_s > 0
    assert props.thermal_conductivity_W_mK > 0
    assert math.isfinite(props.fouling_risk_index)

    q = estimate_stream_volumetric_flow_m3_h(stream, props.liquid_density_kg_m3)
    wide = calculate_pipe_hydraulics(props.liquid_density_kg_m3, props.dynamic_viscosity_Pa_s, q, 10.0, 0.05)
    narrow = calculate_pipe_hydraulics(props.liquid_density_kg_m3, props.dynamic_viscosity_Pa_s, q, 10.0, 0.02)
    assert narrow.pressure_drop_kPa > wide.pressure_drop_kPa >= 0
    assert narrow.pump_power_kW >= 0

    risk_index, risk_level = fluid_fouling_risk(20.0, props.dynamic_viscosity_Pa_s, result.kpis["Mw"], props.kinematic_viscosity_m2_s)
    assert risk_index >= 0
    assert risk_level in {"low", "medium", "high"}
