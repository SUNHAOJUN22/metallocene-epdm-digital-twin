import numpy as np

from epdm_sim.components import load_components
from epdm_sim.streams import Stream
from epdm_sim.thermo import ThermoEngine, mixture_cp_liq, rachford_rice_residual, solve_rachford_rice, thermo_package_available, wilson_k_value


def test_thermo_direct_functions_are_bounded_and_phase_logic_holds():
    comps = load_components()
    assert isinstance(thermo_package_available(), bool)
    for name in ["ethylene", "propylene", "hexane"]:
        assert wilson_k_value(comps[name], 373.15, 1.0e6) > 0

    z = np.array([0.3, 0.7])
    k = np.array([2.0, 0.5])
    vf = solve_rachford_rice(z, k)
    assert 0.0 <= vf <= 1.0
    assert np.isfinite(rachford_rice_residual(vf, z, k))

    stream = Stream.from_mass_flows(
        "test",
        temperature_K=373.15,
        pressure_Pa=1.0e6,
        mass_flows={"ethylene": 2.0, "propylene": 3.0, "hexane": 10.0},
    )
    engine = ThermoEngine()
    split = engine.flash(stream.molar_flows, 373.15, 2.0e5)
    assert 0.0 <= split.vapor_fraction <= 1.0
    assert split.y
    assert split.x
    assert abs(sum(split.y.values()) - 1.0) < 1e-9
    assert abs(sum(split.x.values()) - 1.0) < 1e-9
    assert mixture_cp_liq({"hexane": 10.0, "ethylene": 1.0}) > 0
