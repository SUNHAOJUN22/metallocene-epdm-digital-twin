from epdm_sim.dimensional_checks import kj_h_to_kw, mol_L_to_mol_m3, run_dimensional_checks


def test_dimensional_conversions_and_checks():
    assert kj_h_to_kw(3600.0) == 1.0
    assert mol_L_to_mol_m3(1.0) == 1000.0
    checks = run_dimensional_checks()
    assert all(check.passed for check in checks)
