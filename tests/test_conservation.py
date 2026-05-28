from epdm_sim.conservation import (
    conservation_dataframe,
    flash_mass_balance,
    product_composition_balance,
    reactor_monomer_polymer_balance,
    run_conservation_checks,
)
from epdm_sim.flowsheet import load_default_config, run_flowsheet


def test_default_conservation_checks_pass_or_warn_only():
    result = run_flowsheet(load_default_config())
    checks = run_conservation_checks(result)
    assert checks
    assert not [check for check in checks if not check.passed and check.severity == "error"]
    assert not conservation_dataframe(checks).empty


def test_reactor_monomer_polymer_balance_closes():
    result = run_flowsheet(load_default_config())
    check = reactor_monomer_polymer_balance(result.reactor)
    assert check.passed


def test_flash_mass_balance_closes():
    result = run_flowsheet(load_default_config())
    check = flash_mass_balance(result.streams["Quenched solution"], result.flash1.vapor, result.flash1.liquid)
    assert check.passed


def test_product_composition_balance_closes():
    result = run_flowsheet(load_default_config())
    check = product_composition_balance(result.kpis)
    assert check.passed


def test_bad_product_composition_returns_failed_not_crash():
    check = product_composition_balance({"C2_wt": 40.0, "C3_wt": 40.0, "ENB_wt": 5.0})
    assert not check.passed
