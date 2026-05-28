from epdm_sim.equation_binding import (
    EquationBinding,
    equation_binding_dataframe,
    import_implementation,
    load_equation_bindings,
    run_equation_binding_checks,
    trend_smoke_results,
    validate_equation_bindings,
)


def test_equation_bindings_importable_for_critical_equations():
    bindings = load_equation_bindings()
    assert isinstance(next(iter(bindings.values())), EquationBinding)
    errors = validate_equation_bindings()
    assert errors == []
    df = equation_binding_dataframe()
    assert not df.empty
    assert df[df["implementation_function"] != ""]["importable"].all()


def test_import_implementation_and_trend_smoke():
    fn = import_implementation("epdm_sim.kinetics.arrhenius")
    assert fn(1.0, 40000.0, 390.0) >= fn(1.0, 40000.0, 350.0)
    checks = run_equation_binding_checks()
    assert not checks.empty
    assert checks["passed"].all()
    trends = trend_smoke_results()
    assert trends["passed"].all()
