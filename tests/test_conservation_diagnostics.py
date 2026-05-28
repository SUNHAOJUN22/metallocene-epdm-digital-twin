from epdm_sim.conservation import ConservationResult, diagnose_conservation_results


def _failed(balance_type):
    return ConservationResult(balance_type, 100, 50, 50, 50, 1, False, "error", "failed", "fix")


def test_diagnose_flash_mismatch_points_to_flash():
    diag = diagnose_conservation_results([_failed("flash_mass_balance:Flash-1 inlet")])[0]
    assert diag.likely_source == "flash"


def test_diagnose_heat_mismatch_points_to_heat_balance():
    diag = diagnose_conservation_results([_failed("energy_release_balance")])[0]
    assert diag.likely_source == "heat_balance"
    assert "deltaH" in diag.suspected_unit_issue


def test_diagnose_composition_mismatch_points_to_product():
    diag = diagnose_conservation_results([_failed("product_composition_balance")])[0]
    assert diag.likely_source == "product_properties"
