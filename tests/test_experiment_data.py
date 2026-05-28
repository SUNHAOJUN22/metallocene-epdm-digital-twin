import pandas as pd

from epdm_sim.experiment_data import calibration_subset, load_internal_experiment_dataset, normalize_experiments, quality_check_experiments


def test_experiment_data_normalizes_internal_aliases():
    df = load_internal_experiment_dataset()
    assert {"run_id", "ethylene_feed", "propylene_feed", "enb_feed", "Mooney"}.issubset(df.columns)
    assert len(df) >= 10
    assert df["pressure_MPa"].notna().all()


def test_experiment_quality_detects_duplicates_and_impossible_values():
    raw = pd.DataFrame(
        {
            "run_id": ["A", "A"],
            "ethylene_g": [10, 20],
            "propylene_g": [20, 30],
            "enb_ml": [2, 3],
            "C2_wt": [55, 150],
            "ENB_wt": [5, 6],
            "Mw": [300000, 320000],
            "mooney": [80, 85],
        }
    )
    norm = normalize_experiments(raw)
    report = quality_check_experiments(norm)
    assert report.duplicate_run_ids == ["A"]
    assert any(item["field"] == "C2_wt" for item in report.impossible_values)
    assert len(calibration_subset(norm)) == 2
