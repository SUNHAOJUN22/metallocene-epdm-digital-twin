from epdm_sim.flash import Flash, diagnose_flash_result
from epdm_sim.streams import Stream


def _flash_stream():
    return Stream(
        name="flash feed",
        temperature_K=373.15,
        pressure_Pa=1.0e6,
        molar_flows={"hydrogen": 5.0, "ethylene": 100.0, "propylene": 50.0, "ENB": 5.0, "hexane": 500.0},
        polymer_mass_kg_h=1.0,
        segment_masses_kg_h={"E": 0.5, "P": 0.4, "D": 0.1},
    )


def test_flash_diagnostic_bounded_and_polymer_nonvolatile():
    result = Flash("diag").calculate(_flash_stream(), 353.15, 2.0e5)
    diag = diagnose_flash_result(result)
    assert 0.0 <= diag.vapor_fraction <= 1.0
    assert diag.component_distribution_flags["polymer_pseudo"] == "nonvolatile"
    assert result.vapor.polymer_mass_kg_h == 0


def test_lower_pressure_increases_or_preserves_vapor_fraction():
    stream = _flash_stream()
    high_p = Flash("high").calculate(stream, 353.15, 5.0e5)
    low_p = Flash("low").calculate(stream, 353.15, 1.0e5)
    assert low_p.vapor_fraction >= high_p.vapor_fraction
