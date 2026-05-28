from epdm_sim.recycle_solver import solve_recycle


def test_recycle_solver_converges_and_reports_recovery():
    result = solve_recycle(
        {"ethylene": 10.0, "propylene": 5.0, "hydrogen": 0.1},
        {"hexane": 20.0, "ENB": 1.0},
        {"ethylene": 20.0, "propylene": 30.0, "hexane": 100.0},
        purge_fraction=0.05,
    )
    assert result.convergence_iterations > 0
    assert result.closure_error < 1.0e-4
    assert result.monomer_recovery_pct > 90
    assert not result.as_dataframe().empty
