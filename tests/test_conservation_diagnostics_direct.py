from epdm_sim.conservation import (
    ConservationResult,
    component_mass_balance,
    conservation_dataframe,
    conservation_diagnostics_dataframe,
    diagnose_conservation_results,
    energy_release_balance,
    flash_mass_balance,
    product_composition_balance,
    run_conservation_checks,
    stream_mass,
)
from epdm_sim.flowsheet import run_flowsheet


def test_conservation_direct_tables_and_diagnostics_are_actionable():
    result = run_flowsheet()
    checks = run_conservation_checks(result)
    assert checks
    assert not conservation_dataframe(checks).empty
    assert component_mass_balance(result, "ethylene").relative_error_pct >= 0
    assert product_composition_balance(result.kpis).passed
    assert stream_mass(result.streams["Feed"]) > 0

    flash_check = flash_mass_balance(
        result.streams["Reactor outlet"],
        result.streams["Flash-1 vapor"],
        result.streams["Flash-1 liquid"],
        tolerance_pct=100.0,
    )
    assert flash_check.balance_type.startswith("flash_mass")

    heat_check = energy_release_balance(result.reactor, result.heat_balance)
    assert heat_check.calculated >= 0

    bad = ConservationResult("flash_mass_balance:Flash-1", 100.0, 80.0, 20.0, 20.0, 1.0, False, "error", "bad flash")
    diagnostics = diagnose_conservation_results([bad])
    assert diagnostics
    assert "flash" in diagnostics[0].likely_source.lower()
    assert not conservation_diagnostics_dataframe(diagnostics).empty
