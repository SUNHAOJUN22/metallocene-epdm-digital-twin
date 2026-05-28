from io import BytesIO
import zipfile

import numpy as np
import pandas as pd

from epdm_sim.benchmark_source_registry import (
    benchmark_lineage_dataframe,
    benchmark_source_registry_dataframe,
    benchmark_source_registry_summary,
    load_benchmark_sources,
)
from epdm_sim.calibrated_property_models import (
    CalibratedPropertyModel,
    apply_calibrated_property_value,
    calibrated_property_usage_dataframe,
    select_calibrated_property_model,
)
from epdm_sim.dynamic_core.stability_checks import (
    dynamic_stability_checks_dataframe,
    dynamic_stability_status,
    stiffness_indicator_from_profile,
)
from epdm_sim.dynamic_template_reactor import simulate_template_semibatch_ode
from epdm_sim.equation_residual_coupling import (
    EquationResidualCoupling,
    equation_residual_coupling_dataframe,
    equation_residual_coupling_summary,
    residual_sources_for_equations,
)
from epdm_sim.flowsheet import load_default_config, run_flowsheet
from epdm_sim.math_core.acceptance import math_core_acceptance, math_core_acceptance_dataframe
from epdm_sim.math_core.constraints import physical_constraints_acceptance, physical_constraints_dataframe
from epdm_sim.math_core.diagnostics import math_core_diagnostics_dataframe
from epdm_sim.math_core.equations import equation_kernel_acceptance, equation_kernel_dataframe
from epdm_sim.math_core.residuals import coerce_residual_system, residual_kernel_acceptance, residual_kernel_dataframe
from epdm_sim.report import export_excel
from epdm_sim.report_consistency import check_excel_required_sheets
from epdm_sim.repro_package import export_repro_package, load_repro_manifest_from_zip
from epdm_sim.residual_acceptance import (
    calibrated_set_residual_acceptance,
    doe_residual_acceptance,
    optimizer_residual_acceptance,
    residual_acceptance_dataframe,
    residual_acceptance_record,
)
from epdm_sim.residual_system import build_flowsheet_residual_system
from epdm_sim.solver_core.bounded_solver import bounded_explicit_step, project_nonnegative
from epdm_sim.solver_core.fallback_policy import fallback_policy_decision
from epdm_sim.solver_core.residual_projection import bounded_residual_projection, residual_projection_penalty
from epdm_sim.solver_core.solver_status import solver_status_dataframe, solver_status_record


def test_equation_residual_coupling_and_math_core_acceptance():
    cfg = load_default_config()
    result = run_flowsheet(cfg)
    residual_system = build_flowsheet_residual_system(result)

    coupling = equation_residual_coupling_dataframe()
    assert not coupling.empty
    assert coupling["passed"].all()
    assert equation_residual_coupling_summary()["passed"]
    assert residual_sources_for_equations()["reaction_heat_release"] == "heat_release_proxy"
    row = EquationResidualCoupling(**coupling.iloc[0].to_dict())
    assert row.as_dict()["equation_id"]

    equations = equation_kernel_dataframe()
    assert not equations.empty
    assert equation_kernel_acceptance()["passed"]

    residual_df = residual_kernel_dataframe(residual_system)
    assert not residual_df.empty
    assert residual_kernel_acceptance(residual_system)["passed"]
    assert coerce_residual_system(residual_system).overall_score >= 70.0

    constraints = physical_constraints_dataframe(result, config=cfg)
    assert not constraints.empty
    assert physical_constraints_acceptance(result, config=cfg)["passed"]

    acceptance = math_core_acceptance(result, config=cfg)
    assert acceptance["passed"]
    assert math_core_acceptance_dataframe(result, config=cfg)["passed"].iloc[0]
    assert set(math_core_diagnostics_dataframe(result, config=cfg)["domain"]) == {"equations", "residuals", "constraints"}


def test_residual_acceptance_and_solver_core_helpers():
    result = run_flowsheet(load_default_config())
    residual_system = build_flowsheet_residual_system(result)

    record = residual_acceptance_record(residual_system, context="calibration")
    assert record["passed"]
    table = residual_acceptance_dataframe(residual_system)
    assert set(table["context"]) >= {"calibration", "optimizer", "doe", "posterior", "uncertainty"}
    assert table["passed"].all()
    assert calibrated_set_residual_acceptance(residual_system)["can_save_calibrated_set"]
    assert optimizer_residual_acceptance(residual_system)["optimizer_penalty"] >= 0.0
    assert doe_residual_acceptance({"residual_system": residual_system})["passed"]

    projected = project_nonnegative([-1.0, 2.0, np.nan])
    assert (projected >= 0.0).all()
    step = bounded_explicit_step([1.0, 2.0], [-3.0, 1.0], 1.0)
    assert (step >= 0.0).all()

    correction = bounded_residual_projection(100.0, 1.0)
    assert correction["accepted"]
    assert correction["corrected"] == 101.0
    assert residual_projection_penalty(residual_system) >= 0.0
    assert not fallback_policy_decision(residual_system)["fallback_recommended"]
    assert not solver_status_record(residual_system, solver_name="explicit")["fallback_recommended"]
    assert not solver_status_dataframe(residual_system, solver_name="explicit").empty


def test_dynamic_stability_proof_style_checks_are_finite():
    dynamic = simulate_template_semibatch_ode(
        "EPDM_EPM_metallocene_solution",
        config=load_default_config(),
        total_time_min=4.0,
        dt_min=2.0,
        solver_mode="explicit_bounded",
    )
    checks = dynamic_stability_checks_dataframe(dynamic)
    assert not checks.empty
    assert dynamic_stability_status(dynamic)["passed"]
    assert np.isfinite(stiffness_indicator_from_profile(dynamic))
    assert dynamic.profile["polymer_mass_kg"].diff().dropna().ge(-1.0e-10).all()


def test_benchmark_source_registry_and_calibrated_property_usage():
    sources = load_benchmark_sources()
    assert len(sources) >= 4
    registry = benchmark_source_registry_dataframe()
    assert not registry.empty
    assert benchmark_source_registry_summary()["passed"]
    assert benchmark_lineage_dataframe()["data_hash"].astype(str).str.len().gt(0).all()
    weights = dict(zip(registry["source_type"], registry["weight"]))
    assert weights["plant"] > weights["synthetic"] > weights["regression_snapshot"]

    calibrated = CalibratedPropertyModel(
        model_id="exp_viscosity_model",
        parameter_type="viscosity",
        parameters={"viscosity_multiplier": 1.2},
        dataset_id="exp_rheology_001",
        data_hash="abc123",
        validity_range={"temperature_C": [80.0, 130.0]},
        uncertainty={"viscosity_multiplier": 0.05},
        source_type="experiment",
        confidence_score=82.0,
    )
    selected = select_calibrated_property_model([calibrated], parameter_type="viscosity", conditions={"temperature_C": 100.0})
    assert selected.model_id == "exp_viscosity_model"
    applied = apply_calibrated_property_value(2.0, selected, "viscosity_multiplier")
    assert applied["passed"]
    assert applied["calibrated_value"] == 1.2
    usage = calibrated_property_usage_dataframe([calibrated], conditions={"temperature_C": 100.0})
    assert not usage.empty
    assert usage["passed"].all()
    assert usage["within_validity"].all()


def test_report_and_repro_include_v5_7_audit_sheets_and_files():
    result = run_flowsheet(load_default_config())
    xlsx = export_excel(result)
    missing = check_excel_required_sheets(xlsx)[0].detail
    assert missing == ""

    package = export_repro_package(result, report_xlsx=xlsx, test_status="v5_7_test")
    manifest = load_repro_manifest_from_zip(package)
    assert manifest["app_version"] == "V6.4 / 0.7.4"
    with zipfile.ZipFile(BytesIO(package)) as zf:
        names = set(zf.namelist())
    assert {
        "benchmark_sources.csv",
        "benchmark_lineage.csv",
        "equation_residual_coupling.csv",
        "residual_acceptance.csv",
        "calibrated_property_usage.csv",
    }.issubset(names)

