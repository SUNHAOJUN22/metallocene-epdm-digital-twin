from epdm_sim.flowsheet import run_flowsheet
from epdm_sim.residual_system import ResidualSystem, make_residual
from epdm_sim.solver_core.solve_path_integrator import (
    solve_path_integrator_dataframe,
    solve_path_integrator_gate,
    solve_recycle_flash_heat_loop,
)


def test_solve_path_integrator_accepts_default_and_rejects_polymer_vapor():
    result = run_flowsheet()
    status = solve_recycle_flash_heat_loop(result)
    df = solve_path_integrator_dataframe(result)
    gate = solve_path_integrator_gate(result)
    assert status["accepted"]
    assert not df.empty
    assert gate["passed"]

    bad = ResidualSystem(phase_residuals=[make_residual("flash_polymer_vapor", "polymer vapor=0", 0.1, 0.0, "kg/h", 1e-12, "flash", "fix", "critical")])
    assert solve_recycle_flash_heat_loop(bad)["rejected"]
    assert not solve_path_integrator_gate(bad)["passed"]

