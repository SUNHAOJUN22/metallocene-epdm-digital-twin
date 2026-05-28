import math

from epdm_sim.flowsheet import run_flowsheet
from epdm_sim.fluid_props import (
    gas_density,
    liquid_density,
    mixture_cp,
    mixture_molecular_weight,
    mixture_vapor_pressure,
    solvent_log_mixed_viscosity,
    thermal_conductivity,
)


def test_more_fluid_props_public_functions_are_finite_and_trending():
    result = run_flowsheet()
    stream = result.streams["Reactor outlet"]

    assert mixture_molecular_weight(stream) > 0
    assert liquid_density(stream) > 0
    assert mixture_cp(stream, "liquid") > 0
    assert mixture_cp(stream, "gas") > 0
    assert gas_density(stream, 373.15, 1.0e6) > gas_density(stream, 373.15, 0.5e6) > 0
    assert solvent_log_mixed_viscosity(stream, 393.15) < solvent_log_mixed_viscosity(stream, 353.15)
    assert thermal_conductivity(stream) > 0
    assert mixture_vapor_pressure(stream, 373.15, 1.0e6) >= 0
    assert all(math.isfinite(value) for value in [mixture_molecular_weight(stream), liquid_density(stream), thermal_conductivity(stream)])

