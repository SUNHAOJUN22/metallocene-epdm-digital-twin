import numpy as np

from epdm_sim.thermo import ThermoEngine, solve_rachford_rice


def test_rachford_rice_solution_between_zero_and_one():
    z = np.array([0.5, 0.5])
    k = np.array([2.0, 0.3])
    vapor_fraction = solve_rachford_rice(z, k)
    assert 0.0 <= vapor_fraction <= 1.0


def test_simple_flash_vapor_fraction_between_zero_and_one():
    thermo = ThermoEngine("Simple Wilson K")
    split = thermo.flash({"ethylene": 100.0, "hexane": 100.0}, 353.15, 2.0e5)
    assert 0.0 <= split.vapor_fraction <= 1.0
    assert split.mode in {"Simple Wilson K", "thermo-backed"}
