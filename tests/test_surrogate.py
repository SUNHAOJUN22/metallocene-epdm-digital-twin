import pandas as pd

from epdm_sim.surrogate import predict_with_surrogate, surrogate_applicability_warning, train_surrogate_from_sensitivity_results, validate_surrogate_physics


def test_surrogate_train_predict_and_physics():
    df = pd.DataFrame(
        {
            "hydrogen_g_h": [0, 5, 10, 20],
            "temperature_C": [90, 100, 110, 120],
            "Mw": [600000, 420000, 300000, 180000],
        }
    )
    model = train_surrogate_from_sensitivity_results(df, "Mw", ["hydrogen_g_h", "temperature_C"])
    pred = predict_with_surrogate(model, {"hydrogen_g_h": 8, "temperature_C": 105})
    assert pred[0] > 0
    checks = validate_surrogate_physics(model)
    assert checks["passed"].all()
    assert surrogate_applicability_warning(model, {"hydrogen_g_h": 100, "temperature_C": 105})
