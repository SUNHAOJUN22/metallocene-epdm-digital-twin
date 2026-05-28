from epdm_sim.thermo_consistency import run_thermo_consistency_checks, thermo_consistency_dataframe


def test_thermo_consistency_checks_pass_default():
    checks = run_thermo_consistency_checks()
    assert checks
    assert not [check for check in checks if not check.passed and check.severity == "error"]
    assert not thermo_consistency_dataframe(checks).empty
