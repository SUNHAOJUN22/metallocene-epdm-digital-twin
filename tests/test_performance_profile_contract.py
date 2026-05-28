from pathlib import Path

from scripts.performance_profile import run_performance_profile


def test_performance_profile_outputs_artifacts():
    df = run_performance_profile()
    assert not df.empty
    assert df["passed"].all()
    assert (df["runtime_s"] >= 0).all()
    assert Path("tmp_smoke_outputs/performance_profile.json").exists()
    assert Path("tmp_smoke_outputs/performance_profile.csv").exists()
