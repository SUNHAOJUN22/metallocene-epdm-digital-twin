import math

from epdm_sim.flowsheet import run_flowsheet
from epdm_sim.residual_system import ResidualSystem, make_residual
from epdm_sim.solver_core.nonlinear_residual_loop import (
    bounded_physical_projection,
    build_flowsheet_residual_equations,
    nonlinear_residual_iteration,
    nonlinear_residual_loop_gate,
    residual_iteration_certificate,
)


def test_nonlinear_loop_accepts_default_and_rejects_physical_errors():
    system = ResidualSystem()
    equations = build_flowsheet_residual_equations(system)
    projection = bounded_physical_projection(system)
    iteration = nonlinear_residual_iteration(system)
    certificate = residual_iteration_certificate(system)
    gate = nonlinear_residual_loop_gate(system)
    assert not equations.empty
    assert projection["accepted"]
    assert not iteration.empty and iteration["accepted"].astype(bool).all()
    assert certificate["residual_norm_after"].fillna(0.0).map(float).map(math.isfinite).all()
    assert gate["passed"]

    bad = ResidualSystem(phase_residuals=[make_residual("flash_polymer_vapor", "polymer vapor=0", 0.2, 0.0, "kg/h", 1e-12, "flash", "fix", "critical")])
    rejected = bounded_physical_projection(bad)
    assert rejected["rejected"]
    assert not nonlinear_residual_loop_gate(bad)["passed"]


def test_nonlinear_loop_residual_norm_does_not_increase_for_flowsheet():
    result = run_flowsheet()
    iteration = nonlinear_residual_iteration(result)
    assert not iteration.empty
    assert (iteration["residual_norm_after"] <= iteration["residual_norm_before"] + 1e-12).all()

