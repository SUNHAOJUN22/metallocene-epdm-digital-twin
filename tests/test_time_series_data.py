import pandas as pd

from epdm_sim.time_series_data import normalize_time_series, validate_time_series_schema


def test_time_series_validation_accepts_monotonic_profile_with_optional_warnings():
    df = pd.DataFrame(
        {
            "run_id": ["r1", "r1", "r1"],
            "time_min": [0, 5, 10],
            "temperature_C": [90, 95, 100],
            "pressure_MPa": [1.0, 1.0, 1.1],
            "viscosity_Pa_s": [0.001, 0.002, 0.003],
        }
    )
    result = validate_time_series_schema(df)
    assert result.passed
    norm = normalize_time_series(df)
    assert norm["temperature_C"].dtype.kind in "fi"


def test_time_series_validation_rejects_nonmonotonic_time():
    df = pd.DataFrame({"run_id": ["r1", "r1"], "time_min": [5, 0]})
    assert not validate_time_series_schema(df).passed
