from epdm_sim.transport_core import TransportCoreCheck, cooling_capacity_kW, pressure_drop_laminar_kPa, run_transport_core_checks


def test_transport_core_trends_and_bounds():
    checks = run_transport_core_checks()
    assert not checks.empty
    assert checks["passed"].all()
    assert checks["value_low"].notna().all()
    assert isinstance(TransportCoreCheck("x", True, 1.0, 2.0, "-", "msg").as_dict(), dict)


def test_pressure_drop_and_cooling_capacity_trends():
    assert pressure_drop_laminar_kPa(2.0, 0.01, 10.0, 0.025) > pressure_drop_laminar_kPa(1.0, 0.01, 10.0, 0.025)
    assert pressure_drop_laminar_kPa(1.0, 0.02, 10.0, 0.025) > pressure_drop_laminar_kPa(1.0, 0.01, 10.0, 0.025)
    assert cooling_capacity_kW(600.0, 50.0) > cooling_capacity_kW(300.0, 50.0)
