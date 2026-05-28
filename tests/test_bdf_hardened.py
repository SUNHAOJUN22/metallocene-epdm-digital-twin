import pytest
import numpy as np
from epdm_sim.dynamic_template_reactor import simulate_template_semibatch_ode
from epdm_sim.flowsheet import load_default_config

def test_bdf_hardened_readiness():
    """Verify that the hardened BDF readiness check allows standard EPDM cases."""
    cfg = load_default_config()
    # Ensure standard pressure (MPa) and catalyst (umol)
    cfg.pressure_MPa = 1.0
    cfg.catalyst_umol_h = 100.0
    
    result = simulate_template_semibatch_ode(
        template_id="EPDM_EPM_metallocene_solution",
        config=cfg,
        total_time_min=2.0,
        solver_mode="solve_ivp_bdf"
    )
    
    # Check if BDF was used instead of fallback
    summary = result.summary
    print(f"\nSolver used: {summary['solver_mode_used']}")
    print(f"Fallback used: {summary['fallback_used']}")
    print(f"Solver message: {summary['solver_message']}")
    
    assert summary['solver_mode_used'] == "solve_ivp_bdf"
    assert summary['fallback_used'] is False
    assert "success" in summary['solver_status']

if __name__ == "__main__":
    test_bdf_hardened_readiness()
