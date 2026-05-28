from epdm_sim.benchmark_reconciliation import (
    benchmark_reconciliation_dataframe,
    benchmark_reconciliation_gate,
    benchmark_reconciliation_summary,
    estimate_measurement_uncertainty,
    reconcile_benchmark_observations,
)
from epdm_sim.industrial_data_package import load_industrial_data_package


def test_benchmark_reconciliation_pass_fail_and_uncertainty():
    package = load_industrial_data_package()
    df = reconcile_benchmark_observations(package, {"polymer_mass_closure": 11.5})
    assert not df.empty and df["passed"].astype(bool).all()
    assert benchmark_reconciliation_summary(package, {"polymer_mass_closure": 11.5})["passed"]
    assert benchmark_reconciliation_gate(package, {"polymer_mass_closure": 11.5})["passed"]
    assert not benchmark_reconciliation_dataframe(package, {"polymer_mass_closure": 11.5}).empty
    assert estimate_measurement_uncertainty(package)["effective_uncertainty"] >= 0.0

    failed = benchmark_reconciliation_summary(package, {"polymer_mass_closure": 100.0})
    assert not failed["passed"]

