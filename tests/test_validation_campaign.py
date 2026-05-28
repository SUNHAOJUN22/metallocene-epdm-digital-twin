import pandas as pd

from epdm_sim.validation_campaign import (
    load_validation_datasets,
    recommend_next_validation_data,
    run_validation_campaign,
    validation_datasets_dataframe,
)


def test_validation_dataset_loads_and_has_required_metadata():
    payload = load_validation_datasets()
    assert str(payload["version"]).startswith("V6.4")
    df = validation_datasets_dataframe()
    assert not df.empty
    endpoint_rows = payload["datasets"][0]["endpoint_rows"]
    assert endpoint_rows
    assert {"run_id", "C2_wt", "ENB_wt", "Mooney"}.issubset(endpoint_rows[0])


def test_validation_campaign_outputs_score_bias_and_recommendations():
    df = pd.DataFrame(
        {
            "run_id": ["synthetic"],
            "C2_wt": [55.0],
            "ENB_wt": [6.0],
            "Mooney": [80.0],
            "Mw": [360000.0],
            "polymer_g": [40.0],
        }
    )
    result = run_validation_campaign(endpoint_data=df)
    assert 0.0 <= result.validation_score <= 100.0
    assert not result.model_bias.empty
    assert not result.recommended_next_data.empty
    assert not recommend_next_validation_data(result.model_bias).empty

