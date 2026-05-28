from epdm_sim.scientific_benchmarks import benchmark_definitions, run_scientific_benchmarks, unit_roundtrip_checks


def test_scientific_benchmarks_are_finite_and_pass():
    definitions = benchmark_definitions()
    assert not definitions.empty
    df = run_scientific_benchmarks()
    assert not df.empty
    assert df["passed"].all()
    assert unit_roundtrip_checks()["passed"].all()
