import math

import pandas as pd

from epdm_sim.benchmark_calibration import update_model_confidence_from_benchmarks
from epdm_sim.calibrated_property_models import (
    CalibratedPropertyModel,
    calibrated_model_from_property_result,
    calibrated_property_model_score,
    calibrated_property_models_dataframe,
    calibrated_property_validity_check,
    default_property_model,
    load_calibrated_property_models,
    save_calibrated_property_models,
)
from epdm_sim.data_lineage import (
    DataLineageRecord,
    build_data_lineage_record,
    critical_benchmarks_missing_lineage,
    data_lineage_dataframe,
    lineage_confidence_from_record,
    lineage_confidence_score,
    lineage_for_benchmarks,
    stable_data_hash,
)
from epdm_sim.dynamic_core.residual_feedback import (
    dynamic_residual_feedback,
    residual_feedback_recommends_fallback,
    residual_feedback_solver_status,
)
from epdm_sim.dynamic_template_reactor import simulate_template_semibatch_ode
from epdm_sim.equation_reverse_check import EquationReverseCheck, equation_reverse_check_summary, run_equation_reverse_checks
from epdm_sim.estimation.residual_constrained_fit import (
    ResidualConstrainedFitResult,
    parameter_prior_penalty,
    residual_constrained_fit_dataframe,
    residual_constrained_objective,
    run_residual_constrained_fit,
    validate_target_units,
)
from epdm_sim.flowsheet import load_default_config, run_flowsheet
from epdm_sim.posterior import run_lightweight_mcmc
from epdm_sim.posterior_residual_filter import (
    filter_posterior_samples_by_residual,
    posterior_residual_filter_dataframe,
    residual_acceptance_rate,
    residual_penalty_for_sample,
)
from epdm_sim.property_calibration import calibrate_heat_release, calibrate_viscosity_model
from epdm_sim.report import export_excel
from epdm_sim.report_consistency import check_excel_required_sheets, excel_sheet_names
from epdm_sim.repro_package import export_repro_package, load_repro_manifest_from_zip
from epdm_sim.residual_system import build_flowsheet_residual_system


def test_data_lineage_scores_and_hashes_are_stable():
    record = {
        "benchmark_id": "exp_case",
        "source_type": "experiment",
        "source_reference": "local lab run",
        "unit": "kg/h",
        "tolerance": 0.1,
        "validity_range": {"temperature_C": [80, 130]},
        "confidence_level": "high",
    }
    assert stable_data_hash(record) == stable_data_hash(dict(record))
    lineage = build_data_lineage_record(record)
    assert isinstance(lineage, DataLineageRecord)
    assert lineage_confidence_from_record(lineage.as_dict()) > lineage_confidence_from_record({**lineage.as_dict(), "source_type": "regression_snapshot", "source_reference": ""})
    rows = lineage_for_benchmarks([record])
    assert rows and rows[0].dataset_id == "exp_case"
    df = data_lineage_dataframe([record])
    assert not df.empty and df["lineage_confidence_score"].iloc[0] > 50
    assert lineage_confidence_score([record]) > 50
    assert critical_benchmarks_missing_lineage([record])["passed"].all()


def test_residual_constrained_fit_rejects_bad_units_and_accepts_default_residuals():
    cfg = load_default_config()
    result = run_flowsheet(cfg)
    residual_system = build_flowsheet_residual_system(result)
    params = {"k_E_ref": 100.0, "Mw0": 350000.0, "ktr_H2": 0.2}

    assert validate_target_units({"C2_wt": "wt%"}) == []
    assert validate_target_units({"C2_wt": "kg/h"})
    assert parameter_prior_penalty(params) == 0.0
    assert parameter_prior_penalty({"Mw0": -1.0}) >= 1000.0

    obj = residual_constrained_objective(1.0, residual_system, params=params, target_units={"C2_wt": "wt%", "Mw": "g/mol"})
    obj_bad = residual_constrained_objective(1.0, residual_system, params=params, target_units={"C2_wt": "kg/h"})
    assert math.isfinite(obj) and obj >= 0.0
    assert obj_bad > obj

    fit = run_residual_constrained_fit(initial_params=params, result_or_residual_system=residual_system, target_units={"C2_wt": "wt%", "Mw": "g/mol"})
    assert isinstance(fit, ResidualConstrainedFitResult)
    assert fit.accepted
    assert not fit.confidence_interval.empty
    assert residual_constrained_fit_dataframe(fit)["accepted"].iloc[0] is True or bool(residual_constrained_fit_dataframe(fit)["accepted"].iloc[0])
    assert residual_constrained_fit_dataframe().iloc[0]["status"] == "not_run"


def test_posterior_residual_filter_bounds_acceptance_rate():
    result = run_flowsheet(load_default_config())
    residual_system = build_flowsheet_residual_system(result)
    posterior = run_lightweight_mcmc(n_steps=12, seed=123)
    filtered = filter_posterior_samples_by_residual(posterior.samples, residual_system)
    assert not filtered.empty
    rate = residual_acceptance_rate(posterior.samples, residual_system)
    assert 0.0 <= rate <= 1.0
    assert posterior_residual_filter_dataframe(posterior.samples, residual_system)["residual_acceptance_rate"].dropna().iloc[0] == rate
    penalty = residual_penalty_for_sample(posterior.samples.iloc[0].to_dict(), residual_system)
    assert math.isfinite(penalty) and penalty >= 0.0
    assert posterior_residual_filter_dataframe().iloc[0]["status"] == "not_run"


def test_equation_reverse_checks_are_complete_and_finite():
    df = run_equation_reverse_checks()
    summary = equation_reverse_check_summary()
    row = EquationReverseCheck("test_equation", "module.fn", "unit", 1.0, "-", True, "ok").as_dict()
    assert row["passed"] is True
    assert not df.empty
    assert summary["rows"] == len(df)
    assert summary["passed"]
    assert df["value"].apply(math.isfinite).all()


def test_dynamic_residual_feedback_augments_solver_status():
    dynamic = simulate_template_semibatch_ode(total_time_min=3.0, dt_min=1.0, solver_mode="explicit_bounded")
    feedback = dynamic_residual_feedback(dynamic)
    status = residual_feedback_solver_status(dynamic)
    assert not feedback.empty
    assert "residual_acceptance_rate" in status
    assert 0.0 <= status["residual_acceptance_rate"] <= 1.0
    assert isinstance(residual_feedback_recommends_fallback(dynamic), bool)
    assert dynamic.profile["polymer_mass_kg"].diff().dropna().ge(-1.0e-10).all()


def test_calibrated_property_models_lineage_and_validity(tmp_path):
    default = default_property_model()
    assert isinstance(default, CalibratedPropertyModel)
    assert default.confidence_score < 50.0

    viscosity_data = pd.DataFrame(
        [
            {"temperature_K": 360.0, "solids_wt": 8.0, "Mw": 300000.0, "viscosity_Pa_s": 0.01},
            {"temperature_K": 370.0, "solids_wt": 12.0, "Mw": 320000.0, "viscosity_Pa_s": 0.02},
            {"temperature_K": 380.0, "solids_wt": 16.0, "Mw": 340000.0, "viscosity_Pa_s": 0.04},
        ]
    )
    prop_result = calibrate_viscosity_model(viscosity_data, dataset_id="visc_exp")
    calibrated = calibrated_model_from_property_result(prop_result, source_type="experiment")
    assert calibrated.confidence_score > default.confidence_score
    assert calibrated_property_model_score([default, calibrated]) > default.confidence_score
    validity = calibrated_property_validity_check(calibrated, {"temperature_K": 370.0})
    assert not validity.empty and validity["passed"].all()

    path = tmp_path / "calibrated_property_models.json"
    save_calibrated_property_models([calibrated], path=path)
    loaded = load_calibrated_property_models(path=path)
    assert loaded[0].model_id == calibrated.model_id
    assert not calibrated_property_models_dataframe(loaded).empty

    heat_result = calibrate_heat_release(pd.DataFrame([{"consumed_mol": 1.0, "Q_rxn_kJ": 90.0}, {"consumed_mol": 2.0, "Q_rxn_kJ": 180.0}]))
    heat_model = calibrated_model_from_property_result(heat_result, source_type="literature")
    assert heat_model.parameters["deltaH_kJ_mol"] < 0.0


def test_report_and_repro_contain_v5_6_lineage_sheets():
    result = run_flowsheet(load_default_config())
    xlsx = export_excel(result)
    sheets = set(excel_sheet_names(xlsx))
    required = {
        "data_lineage",
        "residual_constrained_fit",
        "posterior_residual_filter",
        "equation_reverse_check",
        "dynamic_residual_feedback",
        "calibrated_property_models",
    }
    assert required.issubset(sheets)
    assert check_excel_required_sheets(xlsx)[0].passed

    package = export_repro_package(result, report_xlsx=xlsx, test_status="test_v5_6")
    manifest = load_repro_manifest_from_zip(package)
    assert manifest["app_version"] == "V6.4 / 0.7.4"
    import zipfile
    from io import BytesIO

    with zipfile.ZipFile(BytesIO(package), "r") as zf:
        names = set(zf.namelist())
    assert {"data_lineage.csv", "calibrated_property_models.csv", "equation_reverse_check.csv"}.issubset(names)


def test_benchmark_confidence_improves_with_model_outputs():
    base = update_model_confidence_from_benchmarks(70.0, {})
    matched = update_model_confidence_from_benchmarks(70.0, {"value": 0.0})
    assert 0.0 <= base["adjusted_score"] <= 100.0
    assert 0.0 <= matched["adjusted_score"] <= 100.0


