from epdm_sim.flash import Flash
from epdm_sim.streams import Stream


def test_flash_mass_balance_and_vapor_fraction():
    feed = Stream.from_mass_flows(
        "test feed",
        temperature_K=350.0,
        pressure_Pa=1.0e6,
        mass_flows={"ethylene": 1.0, "propylene": 1.0, "hexane": 10.0},
    )
    result = Flash("test flash").calculate(feed, 360.0, 2.0e5)
    assert 0.0 <= result.vapor_fraction <= 1.0
    mass_in = feed.total_mass_flow()
    mass_out = result.vapor.total_mass_flow() + result.liquid.total_mass_flow()
    assert abs(mass_in - mass_out) / mass_in < 1.0e-6
