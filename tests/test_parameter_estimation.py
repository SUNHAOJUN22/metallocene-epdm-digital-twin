from pathlib import Path

import math

from epdm_sim.experiment_data import load_internal_experiment_dataset
from epdm_sim.parameter_estimation import (
    estimate_parameters,
    get_parameter_set_parameters,
    kinetic_parameters_from_set,
    save_parameter_set,
    set_active_parameter_set,
)


def test_parameter_estimation_returns_finite_params():
    result = estimate_parameters(load_internal_experiment_dataset(), target="combined", max_nfev=20)
    assert "k_E_ref" in result.fitted_params
    assert math.isfinite(result.fitted_params["k_E_ref"])
    assert not result.residuals.empty
    assert not result.confidence_interval.empty
    assert not result.parameter_correlation.empty


def test_parameter_set_save_load_and_kinetics(tmp_path: Path):
    result = estimate_parameters(load_internal_experiment_dataset(), target="ENB_wt", max_nfev=8)
    path = tmp_path / "parameter_sets.json"
    save_parameter_set("test_fit", result.fitted_params, path=path)
    set_active_parameter_set("test_fit", path=path)
    params = get_parameter_set_parameters("test_fit", path=path)
    assert params["k_ENB_ref"] > 0
    kin = kinetic_parameters_from_set("default")
    assert kin.k_E_ref > 0


def test_parameter_estimation_flowsheet_proxy_and_metadata(tmp_path: Path):
    result = estimate_parameters(
        load_internal_experiment_dataset(),
        target="ENB_wt",
        max_nfev=4,
        fit_against_flowsheet=True,
        dataset_id="unit_test_dataset",
    )
    path = tmp_path / "parameter_sets.json"
    registry = save_parameter_set(
        "flowsheet_fit",
        result.fitted_params,
        path=path,
        dataset_id=result.dataset_id,
        fit_method="flowsheet_proxy",
        fitted_targets=["ENB_wt"],
        confidence_interval=result.confidence_interval,
    )
    saved = registry["sets"]["flowsheet_fit"]
    assert saved["dataset_id"] == "unit_test_dataset"
    assert saved["fit_method"] == "flowsheet_proxy"
    assert saved["confidence_interval"]
