from epdm_sim.flowsheet import load_default_config
from epdm_sim.preflight import (
    has_blocking_failures,
    run_preflight_for_cfd,
    run_preflight_for_flowsheet,
    run_preflight_for_model,
    run_preflight_for_optimizer,
)


def test_flowsheet_preflight_default_passes():
    checks = run_preflight_for_flowsheet(load_default_config())
    assert checks
    assert not has_blocking_failures(checks)


def test_flowsheet_preflight_blocks_bad_pressure():
    cfg = load_default_config()
    cfg.pressure_MPa = -1.0
    checks = run_preflight_for_flowsheet(cfg)
    assert has_blocking_failures(checks)


def test_generic_model_preflight_schema_bounds():
    checks = run_preflight_for_model("heat_balance", {"mol_consumed": 1.0, "deltaH": -95.0, "U_A": 600.0})
    assert not has_blocking_failures(checks)


def test_cfd_and_optimizer_preflight():
    cfd_checks = run_preflight_for_cfd({"Nx": 80, "Ny": 40, "viscosity_Pa_s": 0.01, "density_kg_m3": 700, "Cp_kJ_kgK": 2.0, "thermal_conductivity_W_mK": 0.12, "diameter_m": 1.0, "length_m": 2.0, "rpm": 500})
    assert not has_blocking_failures(cfd_checks)
    opt_checks = run_preflight_for_optimizer({"temperature_C": (80, 120)})
    assert not has_blocking_failures(opt_checks)
