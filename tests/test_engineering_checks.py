from epdm_sim.engineering_checks import checks_dataframe, overall_engineering_status, run_engineering_checks
from epdm_sim.flowsheet import load_default_config, run_flowsheet


def test_engineering_checks_run_on_default_flowsheet():
    result = run_flowsheet(load_default_config())
    checks = run_engineering_checks(result)
    df = checks_dataframe(checks)

    assert not df.empty
    assert {"passed", "severity", "affected_module", "message", "suggested_fix"}.issubset(df.columns)
    assert overall_engineering_status(checks) in {"green", "yellow", "red"}
    assert not any((not check.passed and check.severity == "error") for check in checks)
