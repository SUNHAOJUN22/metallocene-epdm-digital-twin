from epdm_sim.equation_tests import run_equation_code_checks


def test_equation_code_checks_pass():
    checks = run_equation_code_checks()
    assert len(checks) >= 10
    failed = [check for check in checks if not check.passed]
    assert not failed, [check.as_dict() for check in failed]

