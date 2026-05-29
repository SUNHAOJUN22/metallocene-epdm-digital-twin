"""Excel report export module."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd

from ..conservation import conservation_dataframe, conservation_diagnostics_dataframe, diagnose_conservation_results, run_conservation_checks
from ..doe_optimal import recommend_optimal_doe
from ..dynamic_stability import dynamic_stability_dataframe
from ..engineering_checks import checks_dataframe, run_engineering_checks
from ..engineering_rules import rules_dataframe
from ..dimensional_checks import dimensional_checks_dataframe
from ..equation_binding import equation_binding_dataframe, run_equation_binding_checks, trend_smoke_results
from ..equation_registry import equation_registry_dataframe
from ..equation_tests import equation_code_checks_dataframe
from ..experimental_benchmark import experimental_benchmarks_dataframe, run_experimental_benchmark_checks
from ..benchmark_calibration import benchmark_calibration_summary, benchmark_residual_dataframe, recommend_calibration_data_gaps
from ..calibrated_property_models import calibrated_property_models_dataframe, calibrated_property_usage_dataframe
from ..data_lineage_graph import build_data_lineage_graph
from ..data_lineage import data_lineage_dataframe
from ..dynamic_core.dae_constraints import dae_constraints_dataframe
from ..dynamic_core.solver_decision import dynamic_solver_decision_dataframe
from ..dynamic_core.solver_policy import dynamic_solver_policy_dataframe
from ..dynamic_core.step_acceptance import dynamic_step_acceptance_dataframe
from ..dynamic_core.adaptive_step_control import adaptive_step_control_dataframe
from ..dynamic_core.adaptive_integrator import adaptive_integrator_dataframe
from ..dynamic_core.event_detection import dynamic_event_detection_dataframe
from ..dynamic_core.event_localization import event_localization_dataframe
from ..dynamic_core.residual_feedback import dynamic_residual_feedback, residual_feedback_solver_status
from ..dynamic_core.stability_checks import dynamic_stability_checks_dataframe
from ..dynamic_core.state_invariants import state_invariants_dataframe
from ..evidence_chain import build_evidence_chain, evidence_gap_dataframe
from ..evidence_chain_score import evidence_chain_score_dataframe, evidence_gap_priority_dataframe
from ..model_confidence_certificate import confidence_certificate_dataframe, validation_data_upgrade_plan
from ..governance_certificate import governance_certificate_dataframe
from ..data_assimilation import data_assimilation_dataframe
from ..calibration_data_package import calibration_data_lineage_dataframe, calibration_package_dataframe
from ..industrial_data_package import industrial_data_lineage_dataframe, industrial_data_package_dataframe
from ..benchmark_reconciliation import benchmark_reconciliation_dataframe
from ..equation_residual_coupling import equation_residual_coupling_dataframe
from ..equation_reverse_check import run_equation_reverse_checks
from ..estimation.residual_constrained_fit import residual_constrained_fit_dataframe
from ..flash import diagnose_flash_result
from ..file_security import export_metadata
from ..identifiability import evaluate_identifiability
from ..io_schema import io_schema_dataframe
from ..kpi_adapter import build_template_kpis
from ..kpi_schema import kpis_to_dataframe
from ..model_audit_report import build_model_audit_report
from ..model_confidence_engine import confidence_decomposition, model_confidence_engine_dataframe, recommend_high_value_validation_data
from ..model_confidence import build_model_confidence_card
from ..model_contracts import contracts_dataframe
from ..model_graph import build_equation_graph, model_traceability_dataframe
from ..model_registry import module_trigger_dataframe, registry_summary
from ..property_model_selector import property_model_selection_dataframe
from ..property_model_bridge import property_model_bridge_dataframe
from ..property_model_runtime import property_model_runtime_dataframe
from ..property_runtime_context import property_runtime_context_dataframe
from ..property_runtime_audit import property_runtime_audit_dataframe
from ..property_confidence import property_confidence_dataframe, propagate_property_uncertainty_to_model_confidence
from ..polymer_props import load_target_grades
from ..plot_validation import plot_validation_dataframe
from ..plotting import composition_bar, conversion_bar, sankey_material
from ..preflight import preflight_dataframe, run_preflight_for_flowsheet
from ..property_models import property_models_dataframe
from ..reaction_templates import templates_dataframe
from ..rheology import rheology_models_dataframe
from ..surrogate import SurrogateModel, validate_surrogate_physics
from ..template_config import process_config_to_template_config, template_config_dict
from ..template_flowsheet import template_mass_balance
from ..thermo_consistency import run_thermo_consistency_checks, thermo_consistency_dataframe
from ..ui_audit import run_ui_audit, ui_audit_dataframe
from ..ui_workflow import ui_actions_dataframe
from ..posterior import PosteriorResult
from ..posterior_residual_filter import posterior_residual_filter_dataframe
from ..constrained_window import constrained_windows_dataframe
from ..audit_trail import AuditTrailRecord, audit_trail_dataframe, create_audit_record
from ..aspen_bridge import aspen_bridge_summary, aspen_export_tables
from ..workflow_wizard import workflow_status
from ..cfd.grid_convergence import CFDGridConvergenceResult
from ..validation_campaign import run_validation_campaign
from ..validity_envelope import run_validity_envelope_for_config, validity_envelope_dataframe
from ..report_consistency import report_consistency_dataframe
from ..residual_system import build_flowsheet_residual_system, residual_system_dataframe
from ..residual_objective import residual_diagnostics_dataframe
from ..residual_aware_decision import residual_aware_decision_dataframe
from ..residual_aware_doe import residual_aware_doe_dataframe
from ..residual_aware_optimizer import residual_aware_optimizer_dataframe
from ..residual_aware_sampling import residual_aware_sampling_dataframe
from ..residual_aware_decision_engine import residual_decision_engine_dataframe
from ..residual_solver import residual_correction_trace_dataframe, residual_solver_dataframe
from ..residual_acceptance import residual_acceptance_dataframe
from ..residual_graph import build_residual_graph
from ..benchmark_source_registry import benchmark_lineage_dataframe, benchmark_source_registry_dataframe
from ..dimensioned import as_dimensioned, unit_conversion_trace_dataframe
from ..solver_core.constrained_solver import constrained_solver_dataframe
from ..solver_core.conservation_correction import correction_certificate_dataframe
from ..solver_core.conservation_solve_path import conservation_solve_certificate_dataframe
from ..solver_core.conservation_jacobian import conservation_jacobian_dataframe
from ..solver_core.equation_oriented_solver import equation_oriented_solver_certificate
from ..solver_core.nonlinear_residual_loop import residual_iteration_certificate
from ..solver_core.solve_path_integrator import solve_path_integrator_dataframe
from ..solver_core.residual_minimizer import residual_minimizer_dataframe
from ..solver_core.solver_certificates import solver_certificate_dataframe
from ..ode_diagnostics import rhs_term_schema_dataframe, rhs_terms_diagnostics_dataframe
from ..dynamic_residuals import dynamic_residuals_dataframe
from ..dynamic_core.rhs_terms import rhs_terms_from_profile
from ..dynamic_core.residual_timeseries import dynamic_residual_timeseries
from ..parameter_constraints import parameter_constraints_dataframe
from ..phase_equilibrium_constraints import phase_equilibrium_constraints_dataframe
from ..scientific_benchmarks import benchmark_definitions
from ..thermo_consistency import thermo_physical_constraints_dataframe
from ..transport_core import run_transport_core_checks, transport_physical_constraints_dataframe
from ..validation_evidence import validation_evidence_dataframe


def export_excel(
    result,
    sensitivity_df: pd.DataFrame | None = None,
    optimization: Any | None = None,
    calibration: Any | None = None,
    doe_df: pd.DataFrame | None = None,
    scaleup_df: pd.DataFrame | None = None,
    experiment_data: pd.DataFrame | None = None,
    data_quality: Any | None = None,
    parameter_sets_df: pd.DataFrame | None = None,
    parameter_estimation: Any | None = None,
    dynamic_semibatch_df: pd.DataFrame | None = None,
    case_comparison: pd.DataFrame | None = None,
    recycle_solver: Any | None = None,
    safety: Any | None = None,
    pareto_df: pd.DataFrame | None = None,
    uncertainty: Any | None = None,
    model_confidence: dict[str, Any] | pd.DataFrame | None = None,
    recipe_df: pd.DataFrame | None = None,
    task_log: pd.DataFrame | None = None,
    manifest: dict[str, Any] | None = None,
    calibration_loop_result: Any | None = None,
    model_audit: Any | None = None,
    time_series_df: pd.DataFrame | None = None,
    profile_residuals: pd.DataFrame | None = None,
    bayesian_doe_df: pd.DataFrame | None = None,
    surrogate_model: SurrogateModel | None = None,
    repro_manifest: dict[str, Any] | None = None,
    posterior: PosteriorResult | None = None,
    constrained_windows: pd.DataFrame | None = None,
    audit_records: list[AuditTrailRecord] | None = None,
    workflow_df: pd.DataFrame | None = None,
    cfd_grid_convergence: CFDGridConvergenceResult | pd.DataFrame | None = None,
    validation_campaign: Any | None = None,
) -> bytes:
    """Build an Excel workbook containing streams, units and KPI tables."""
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        result.stream_table().to_excel(writer, sheet_name="stream table", index=False)
        result.unit_table().to_excel(writer, sheet_name="unit operations", index=False)
        template_cfg = process_config_to_template_config(result.config)
        pd.DataFrame([template_config_dict(template_cfg)]).to_excel(writer, sheet_name="template_config", index=False)
        pd.DataFrame(
            [
                {"section": "mass_balance", "name": key, "value": value}
                for key, value in template_mass_balance(result).items()
            ]
            + [
                {"section": "kpi", "name": key, "value": value}
                for key, value in result.kpis.items()
                if isinstance(value, (int, float, str))
            ]
        ).to_excel(writer, sheet_name="template_flowsheet", index=False)
        pd.DataFrame([result.kpis]).drop(columns=["recommendations"], errors="ignore").to_excel(
            writer, sheet_name="product properties", index=False
        )
        all_plot_validation = plot_validation_dataframe(
            {
                "sankey_material": sankey_material(result),
                "conversion_bar": conversion_bar(result),
                "composition_bar": composition_bar(result),
            }
        )
        all_plot_validation.to_excel(writer, sheet_name="plot_validation", index=False)
        all_plot_validation.to_excel(writer, sheet_name="all_plot_validation", index=False)
        pd.DataFrame(
            [
                export_metadata(
                    version="V6.4 / 0.7.4",
                    config=result.config,
                    parameter_set_id=getattr(result.config, "parameter_set_id", "default"),
                    template_id=template_cfg.template_id,
                    model_registry=registry_summary(),
                    equation_registry=equation_registry_dataframe().to_dict(orient="records"),
                    warnings=list(getattr(result, "warnings", [])),
                    missing_heavy_tasks=["dynamic_ode", "cfd", "optimization", "posterior", "doe"],
                )
            ]
        ).to_excel(writer, sheet_name="export_metadata", index=False)
        kpis_to_dataframe(build_template_kpis("EPDM_EPM_metallocene_solution", result)).to_excel(writer, sheet_name="template_kpis", index=False)
        pd.DataFrame([result.kpis]).drop(columns=["recommendations"], errors="ignore").to_excel(writer, sheet_name="application_kpis", index=False)
        pd.DataFrame(
            [
                as_dimensioned(getattr(result.config, "temperature_C", 100.0), "°C", field="temperature").to("K").as_dict(),
                as_dimensioned(getattr(result.config, "pressure_MPa", 1.0), "MPa", field="pressure").to("Pa").as_dict(),
                as_dimensioned(getattr(result.config, "residence_time_min", 30.0), "min", field="residence_time").as_dict(),
                as_dimensioned(getattr(result.config, "pipe_diameter_m", 0.05), "m", field="pipe_diameter").as_dict(),
            ]
        ).to_excel(writer, sheet_name="dimensioned_inputs", index=False)
        unit_conversion_trace_dataframe().to_excel(writer, sheet_name="unit_conversion_trace", index=False)
        for sheet_name, table in aspen_export_tables(result).items():
            table.to_excel(writer, sheet_name=sheet_name[:31], index=False)
        pd.DataFrame([aspen_bridge_summary(result)]).to_excel(writer, sheet_name="aspen_bridge_summary", index=False)
        pd.DataFrame([{"status": "not_run", "note": "Dynamic template ODE profile was not supplied; report export does not run heavy ODE tasks."}]).to_excel(writer, sheet_name="template_ode_rhs", index=False)
        rhs_term_schema_dataframe().to_excel(writer, sheet_name="ode_diagnostics", index=False)
        rhs_terms_diagnostics_dataframe().to_excel(writer, sheet_name="rhs_diagnostics", index=False)
        rhs_terms_from_profile(type("DynamicExport", (), {"profile": dynamic_semibatch_df if dynamic_semibatch_df is not None else pd.DataFrame()})()).to_excel(writer, sheet_name="rhs_term_diagnostics", index=False)
        pd.DataFrame([{"status": "not_run", "note": "No ODE solver diagnostics were supplied; run the dynamic template task first to populate this sheet."}]).to_excel(writer, sheet_name="ode_solver_diagnostics", index=False)
        result.reactor.stage_dataframe().to_excel(writer, sheet_name="reactor profile", index=False)
        result.flash1.split_table.to_excel(writer, sheet_name="flash1 split", index=False)
        result.flash2.split_table.to_excel(writer, sheet_name="flash2 split", index=False)
        result.heat_balance_table().to_excel(writer, sheet_name="heat balance", index=False)
        result.fluid_property_table().to_excel(writer, sheet_name="fluid properties", index=False)
        result.pipe_hydraulics_table().to_excel(writer, sheet_name="pressure drop", index=False)
        checks_dataframe(run_engineering_checks(result)).to_excel(writer, sheet_name="engineering_checks", index=False)
        conservation_checks = run_conservation_checks(result)
        conservation_dataframe(conservation_checks).to_excel(writer, sheet_name="conservation", index=False)
        conservation_diagnostics_dataframe(diagnose_conservation_results(conservation_checks)).to_excel(writer, sheet_name="conservation_diag", index=False)
        residual_df = residual_system_dataframe(build_flowsheet_residual_system(result))
        residual_df.to_excel(writer, sheet_name="residual_system", index=False)
        residual_df.to_excel(writer, sheet_name="residual_system_detailed", index=False)
        residual_diagnostics_dataframe(result).to_excel(writer, sheet_name="residual_objective", index=False)
        residual_acceptance_dataframe(build_flowsheet_residual_system(result)).to_excel(writer, sheet_name="residual_acceptance", index=False)
        residual_solver_dataframe(result).to_excel(writer, sheet_name="residual_solver", index=False)
        residual_correction_trace_dataframe().to_excel(writer, sheet_name="residual_correction_trace", index=False)
        correction_certificate_dataframe(build_flowsheet_residual_system(result)).to_excel(writer, sheet_name="conservation_correction", index=False)
        correction_certificate_dataframe(build_flowsheet_residual_system(result)).to_excel(writer, sheet_name="correction_certificates", index=False)
        conservation_solve_certificate_dataframe(build_flowsheet_residual_system(result)).to_excel(writer, sheet_name="conservation_solve_path", index=False)
        conservation_solve_certificate_dataframe(build_flowsheet_residual_system(result)).to_excel(writer, sheet_name="conservation_solve_cert", index=False)
        equation_oriented_solver_certificate(build_flowsheet_residual_system(result)).to_excel(writer, sheet_name="equation_oriented_solver", index=False)
        conservation_jacobian_dataframe(build_flowsheet_residual_system(result)).to_excel(writer, sheet_name="conservation_jacobian", index=False)
        residual_iteration_certificate(build_flowsheet_residual_system(result)).to_excel(writer, sheet_name="nonlinear_residual_loop", index=False)
        solve_path_integrator_dataframe(build_flowsheet_residual_system(result)).to_excel(writer, sheet_name="solve_path_integrator", index=False)
        constrained_solver_dataframe(result).to_excel(writer, sheet_name="constrained_solver", index=False)
        residual_minimizer_dataframe(build_flowsheet_residual_system(result)).to_excel(writer, sheet_name="residual_minimizer", index=False)
        solver_certificate_dataframe(result).to_excel(writer, sheet_name="solver_certificates", index=False)
        rules_dataframe().to_excel(writer, sheet_name="engineering_rules", index=False)
        equation_registry_dataframe().to_excel(writer, sheet_name="equation_registry", index=False)
        equation_binding_dataframe().to_excel(writer, sheet_name="equation_binding", index=False)
        equation_residual_coupling_dataframe().to_excel(writer, sheet_name="equation_residual_coupling", index=False)
        build_equation_graph().to_excel(writer, sheet_name="equation_graph", index=False)
        build_residual_graph(build_flowsheet_residual_system(result)).to_excel(writer, sheet_name="residual_graph", index=False)
        build_data_lineage_graph().to_excel(writer, sheet_name="data_lineage_graph", index=False)
        model_traceability_dataframe().to_excel(writer, sheet_name="model_traceability_graph", index=False)
        run_equation_binding_checks().to_excel(writer, sheet_name="equation_binding_checks", index=False)
        trend_smoke_results().to_excel(writer, sheet_name="dimensional_signature", index=False)
        module_trigger_dataframe().to_excel(writer, sheet_name="model_registry_snapshot", index=False)
        pd.DataFrame([registry_summary()]).to_excel(writer, sheet_name="registry_summary", index=False)
        equation_code_checks_dataframe().to_excel(writer, sheet_name="equation_code_checks", index=False)
        dimensional_checks_dataframe().to_excel(writer, sheet_name="dimensional_checks", index=False)
        preflight_dataframe(run_preflight_for_flowsheet(result.config)).to_excel(writer, sheet_name="preflight", index=False)
        validity_envelope_dataframe(run_validity_envelope_for_config(result.config)).to_excel(writer, sheet_name="validity_envelope", index=False)
        validity_envelope_dataframe(run_validity_envelope_for_config(result.config)).to_excel(writer, sheet_name="extrapolation_risk", index=False)
        io_schema_dataframe().to_excel(writer, sheet_name="io_schema", index=False)
        ui_actions_dataframe().to_excel(writer, sheet_name="ui_actions", index=False)
        ui_audit_dataframe(run_ui_audit()).to_excel(writer, sheet_name="ui_audit", index=False)
        build_model_confidence_card(result, conservation_results=conservation_checks, preflight_results=run_preflight_for_flowsheet(result.config)).as_dataframe().to_excel(
            writer, sheet_name="model_confidence_card", index=False
        )
        templates_dataframe().to_excel(writer, sheet_name="reaction_templates", index=False)
        templates_dataframe().to_excel(writer, sheet_name="kinetics_template", index=False)
        property_models_dataframe().to_excel(writer, sheet_name="property_model", index=False)
        rheology_models_dataframe().to_excel(writer, sheet_name="rheology", index=False)
        property_confidence_dataframe().to_excel(writer, sheet_name="property_confidence", index=False)
        pd.DataFrame([propagate_property_uncertainty_to_model_confidence()]).drop(columns=["records"], errors="ignore").to_excel(writer, sheet_name="property_conf_score", index=False)
        pd.concat(
            [
                diagnose_flash_result(result.flash1).as_dataframe().assign(unit="flash1"),
                diagnose_flash_result(result.flash2).as_dataframe().assign(unit="flash2"),
            ],
            ignore_index=True,
        ).to_excel(writer, sheet_name="flash_diagnostics", index=False)
        if calibration_loop_result is not None:
            calibration_loop_result.as_dataframe().to_excel(writer, sheet_name="calibration_loop", index=False)
            calibration_loop_result.expected_information_gain.to_excel(writer, sheet_name="calibration_loop_gain", index=False)
        else:
            pd.DataFrame([{"status": "not_run"}]).to_excel(writer, sheet_name="calibration_loop", index=False)
        audit = model_audit or build_model_audit_report(result)
        audit.as_dataframe().to_excel(writer, sheet_name="model_audit", index=False)
        audit.top_risks.to_excel(writer, sheet_name="model_audit_risks", index=False)
        audit.recommended_next_actions.to_excel(writer, sheet_name="model_audit_actions", index=False)
        model_confidence_engine_dataframe(residual_system=build_flowsheet_residual_system(result), model_outputs=result.kpis).to_excel(writer, sheet_name="model_confidence", index=False)
        confidence_decomposition(residual_system=build_flowsheet_residual_system(result), model_outputs=result.kpis).to_excel(writer, sheet_name="confidence_decomposition", index=False)
        validation_evidence_dataframe().to_excel(writer, sheet_name="validation_evidence", index=False)
        recommend_high_value_validation_data().to_excel(writer, sheet_name="validation_data_gaps", index=False)
        pd.DataFrame(
            [
                {
                    "kinetic_calibration_score": 35.0 if parameter_estimation is None and calibration is None else 75.0,
                    "property_calibration_score": 35.0,
                    "thermo_calibration_score": 35.0,
                    "validation_data_score": 35.0 if experiment_data is None or experiment_data.empty else 70.0,
                    "note": "Audit proxy scores; improve with local endpoint/time-series/property/VLE datasets.",
                }
            ]
        ).to_excel(writer, sheet_name="calibration_scores", index=False)
        if time_series_df is not None and not time_series_df.empty:
            time_series_df.to_excel(writer, sheet_name="time_series_data", index=False)
        else:
            pd.DataFrame([{"status": "not_run"}]).to_excel(writer, sheet_name="time_series_data", index=False)
        if profile_residuals is not None and not profile_residuals.empty:
            profile_residuals.to_excel(writer, sheet_name="profile_residuals", index=False)
        else:
            pd.DataFrame([{"status": "not_run"}]).to_excel(writer, sheet_name="profile_residuals", index=False)
        if bayesian_doe_df is not None and not bayesian_doe_df.empty:
            bayesian_doe_df.to_excel(writer, sheet_name="bayesian_doe", index=False)
        else:
            pd.DataFrame([{"status": "not_run"}]).to_excel(writer, sheet_name="bayesian_doe", index=False)
        if surrogate_model is not None:
            surrogate_model.as_dataframe().to_excel(writer, sheet_name="surrogate_model", index=False)
            validate_surrogate_physics(surrogate_model).to_excel(writer, sheet_name="surrogate_validation", index=False)
        else:
            pd.DataFrame([{"status": "not_run"}]).to_excel(writer, sheet_name="surrogate_model", index=False)
            pd.DataFrame([{"status": "not_run"}]).to_excel(writer, sheet_name="surrogate_validation", index=False)
        if posterior is not None:
            posterior.parameter_summary.to_excel(writer, sheet_name="posterior_summary", index=False)
            posterior.samples.to_excel(writer, sheet_name="posterior_samples", index=False)
        else:
            pd.DataFrame([{"status": "not_run"}]).to_excel(writer, sheet_name="posterior_summary", index=False)
            pd.DataFrame([{"status": "not_run"}]).to_excel(writer, sheet_name="posterior_samples", index=False)
        if constrained_windows is not None and not constrained_windows.empty:
            constrained_windows.to_excel(writer, sheet_name="constrained_windows", index=False)
        else:
            pd.DataFrame([{"status": "not_run"}]).to_excel(writer, sheet_name="constrained_windows", index=False)
        audit_records = audit_records or [
            create_audit_record(
                "export_excel",
                "report_export",
                template_config_dict(template_cfg),
                {"xlsx": "generated"},
                parameter_set_id=getattr(result.config, "parameter_set_id", "default"),
                template_id=template_cfg.template_id,
                status="success",
            )
        ]
        audit_trail_dataframe(audit_records).to_excel(writer, sheet_name="audit_trail", index=False)
        (workflow_df if workflow_df is not None else workflow_status()).to_excel(writer, sheet_name="workflow_wizard", index=False)
        if cfd_grid_convergence is not None:
            cfd_df = cfd_grid_convergence.as_dataframe() if hasattr(cfd_grid_convergence, "as_dataframe") else cfd_grid_convergence
            cfd_df.to_excel(writer, sheet_name="cfd_grid_convergence", index=False)
        else:
            pd.DataFrame([{"status": "not_run"}]).to_excel(writer, sheet_name="cfd_grid_convergence", index=False)
        perf_path = Path("tmp_smoke_outputs/performance_profile.csv")
        if perf_path.exists():
            pd.read_csv(perf_path).to_excel(writer, sheet_name="performance_profile", index=False)
        else:
            pd.DataFrame([{"status": "not_run", "note": "Run scripts/performance_profile.py to populate performance data."}]).to_excel(writer, sheet_name="performance_profile", index=False)
        report_consistency_dataframe(task_status=task_log).to_excel(writer, sheet_name="report_consistency", index=False)
        campaign = validation_campaign or run_validation_campaign(config=result.config)
        campaign.as_dataframe().to_excel(writer, sheet_name="validation_campaign", index=False)
        campaign.model_bias.to_excel(writer, sheet_name="validation_model_bias", index=False)
        campaign.recommended_next_data.to_excel(writer, sheet_name="validation_next_data", index=False)
        pd.DataFrame([repro_manifest or {"status": "not_exported"}]).to_excel(writer, sheet_name="repro_manifest", index=False)
        ident = evaluate_identifiability(config=result.config)
        ident.sensitivity_matrix.to_excel(writer, sheet_name="identifiability", index=False)
        ident.parameter_correlation.reset_index(names="parameter").to_excel(writer, sheet_name="param_correlation", index=False)
        recommend_optimal_doe(result.config).recommendations.to_excel(writer, sheet_name="doe_optimal", index=False)
        thermo_consistency_dataframe(run_thermo_consistency_checks()).to_excel(writer, sheet_name="thermo_consistency", index=False)
        thermo_consistency_dataframe(run_thermo_consistency_checks()).to_excel(writer, sheet_name="thermo_math_core", index=False)
        thermo_physical_constraints_dataframe().to_excel(writer, sheet_name="thermo_physical_constraints", index=False)
        phase_equilibrium_constraints_dataframe(result).to_excel(writer, sheet_name="phase_equilibrium_constraints", index=False)
        run_experimental_benchmark_checks().to_excel(writer, sheet_name="experimental_benchmarks", index=False)
        benchmark_source_registry_dataframe().to_excel(writer, sheet_name="benchmark_sources", index=False)
        benchmark_lineage_dataframe().to_excel(writer, sheet_name="benchmark_lineage", index=False)
        data_lineage_dataframe().to_excel(writer, sheet_name="data_lineage", index=False)
        data_lineage_dataframe().to_excel(writer, sheet_name="calibration_lineage", index=False)
        calibration_package_dataframe().to_excel(writer, sheet_name="calibration_data_package", index=False)
        calibration_data_lineage_dataframe().to_excel(writer, sheet_name="calibration_data_lineage", index=False)
        data_assimilation_dataframe().to_excel(writer, sheet_name="data_assimilation", index=False)
        industrial_data_package_dataframe().to_excel(writer, sheet_name="industrial_data_package", index=False)
        industrial_data_lineage_dataframe().to_excel(writer, sheet_name="industrial_data_lineage", index=False)
        benchmark_reconciliation_dataframe(model_outputs=result.kpis).to_excel(writer, sheet_name="benchmark_reconciliation", index=False)
        residual_constrained_fit_dataframe().to_excel(writer, sheet_name="residual_constrained_fit", index=False)
        run_equation_reverse_checks().to_excel(writer, sheet_name="equation_reverse_check", index=False)
        calibrated_property_models_dataframe().to_excel(writer, sheet_name="calibrated_property_models", index=False)
        calibrated_property_usage_dataframe().to_excel(writer, sheet_name="calibrated_property_usage", index=False)
        property_model_selection_dataframe(conditions={"temperature_C": getattr(result.config, "temperature_C", 100.0)}).to_excel(writer, sheet_name="property_model_selection", index=False)
        property_model_bridge_dataframe(conditions={"temperature_C": getattr(result.config, "temperature_C", 100.0)}).to_excel(writer, sheet_name="property_model_bridge", index=False)
        property_model_runtime_dataframe(conditions={"temperature_C": getattr(result.config, "temperature_C", 100.0), "pressure_MPa": getattr(result.config, "pressure_MPa", 1.0), "solids_wt": result.kpis.get("solids_wt", 10.0)}).to_excel(writer, sheet_name="property_model_runtime", index=False)
        property_runtime_context_dataframe(result, conditions={"temperature_C": getattr(result.config, "temperature_C", 100.0), "pressure_MPa": getattr(result.config, "pressure_MPa", 1.0), "solids_wt": result.kpis.get("solids_wt", 10.0)}).to_excel(writer, sheet_name="property_runtime_context", index=False)
        property_runtime_audit_dataframe(result, conditions={"temperature_C": getattr(result.config, "temperature_C", 100.0), "pressure_MPa": getattr(result.config, "pressure_MPa", 1.0), "solids_wt": result.kpis.get("solids_wt", 10.0)}).to_excel(writer, sheet_name="property_runtime_audit", index=False)
        run_transport_core_checks().to_excel(writer, sheet_name="transport_core", index=False)
        transport_physical_constraints_dataframe().to_excel(writer, sheet_name="transport_physical_constraints", index=False)
        parameter_constraints_dataframe().to_excel(writer, sheet_name="parameter_constraints", index=False)
        benchmark_definitions().to_excel(writer, sheet_name="benchmark_acceptance", index=False)
        benchmark_calibration_summary(result.kpis).to_excel(writer, sheet_name="benchmark_calibration", index=False)
        benchmark_residual_dataframe(result.kpis).to_excel(writer, sheet_name="benchmark_residuals", index=False)
        recommend_calibration_data_gaps(result.kpis).to_excel(writer, sheet_name="benchmark_data_gaps", index=False)
        posterior_residual_filter_dataframe(
            posterior.samples if posterior is not None else None,
            build_flowsheet_residual_system(result) if posterior is not None else None,
        ).to_excel(writer, sheet_name="posterior_residual_filter", index=False)
        pd.DataFrame([{"status": "not_run", "note": "Posterior samples are not supplied to report export; export remains read-only."}]).to_excel(writer, sheet_name="posterior_residual_acceptance", index=False)
        pd.DataFrame([{"status": "not_run", "note": "Uncertainty residual risk requires an uncertainty task result."}]).to_excel(writer, sheet_name="uncertainty_residual_risk", index=False)
        pd.DataFrame(
            [
                {"source": "dynamic_ode", "fallback_status": "not_run", "reason": "report export is read-only"},
                {"source": "thermo_eos", "fallback_status": "diagnostics_recorded", "reason": "see thermo_physical_constraints"},
                {"source": "flash", "fallback_status": "diagnostics_recorded", "reason": "see flash_diagnostics"},
            ]
        ).to_excel(writer, sheet_name="fallback_diagnostics", index=False)
        if dynamic_semibatch_df is not None and not dynamic_semibatch_df.empty:
            from ..dynamic_stability import check_dynamic_stability
            dynamic_export = type("DynamicExport", (), {"profile": dynamic_semibatch_df, "summary": {}})()
            dynamic_stability_dataframe(check_dynamic_stability(dynamic_semibatch_df)).to_excel(writer, sheet_name="dynamic_stability", index=False)
            dynamic_residuals_dataframe(dynamic_export).to_excel(writer, sheet_name="dynamic_residuals", index=False)
            dynamic_residual_timeseries(dynamic_export).to_excel(writer, sheet_name="dynamic_residual_timeseries", index=False)
            dynamic_residual_feedback(dynamic_export).to_excel(writer, sheet_name="dynamic_residual_feedback", index=False)
            dynamic_solver_decision_dataframe(dynamic_export).to_excel(writer, sheet_name="dynamic_solver_decision", index=False)
            dynamic_solver_policy_dataframe(dynamic_export).to_excel(writer, sheet_name="dynamic_solver_policy", index=False)
            dynamic_step_acceptance_dataframe(dynamic_export).to_excel(writer, sheet_name="dynamic_step_acceptance", index=False)
            adaptive_step_control_dataframe(dynamic_export).to_excel(writer, sheet_name="adaptive_step_control", index=False)
            dynamic_event_detection_dataframe(dynamic_export).to_excel(writer, sheet_name="dynamic_event_detection", index=False)
            adaptive_integrator_dataframe(dynamic_export).to_excel(writer, sheet_name="adaptive_integrator", index=False)
            event_localization_dataframe(dynamic_export).to_excel(writer, sheet_name="event_localization", index=False)
            dynamic_stability_checks_dataframe(dynamic_export).to_excel(writer, sheet_name="dynamic_stability_checks", index=False)
            dae_constraints_dataframe(dynamic_export).to_excel(writer, sheet_name="dae_constraints", index=False)
            state_invariants_dataframe(dynamic_export).to_excel(writer, sheet_name="state_invariants", index=False)
            pd.DataFrame([residual_feedback_solver_status(dynamic_export)]).to_excel(writer, sheet_name="dyn_resid_feedback_status", index=False)
        else:
            pd.DataFrame([{"status": "not_run"}]).to_excel(writer, sheet_name="dynamic_stability", index=False)
            pd.DataFrame([{"status": "not_run"}]).to_excel(writer, sheet_name="dynamic_residuals", index=False)
            pd.DataFrame([{"status": "not_run"}]).to_excel(writer, sheet_name="dynamic_residual_timeseries", index=False)
            pd.DataFrame([{"status": "not_run"}]).to_excel(writer, sheet_name="dynamic_residual_feedback", index=False)
            pd.DataFrame([{"status": "not_run"}]).to_excel(writer, sheet_name="dynamic_solver_decision", index=False)
            dynamic_solver_policy_dataframe().to_excel(writer, sheet_name="dynamic_solver_policy", index=False)
            dynamic_step_acceptance_dataframe().to_excel(writer, sheet_name="dynamic_step_acceptance", index=False)
            adaptive_step_control_dataframe().to_excel(writer, sheet_name="adaptive_step_control", index=False)
            dynamic_event_detection_dataframe().to_excel(writer, sheet_name="dynamic_event_detection", index=False)
            adaptive_integrator_dataframe().to_excel(writer, sheet_name="adaptive_integrator", index=False)
            event_localization_dataframe().to_excel(writer, sheet_name="event_localization", index=False)
            pd.DataFrame([{"status": "not_run"}]).to_excel(writer, sheet_name="dynamic_stability_checks", index=False)
            pd.DataFrame([{"status": "not_run"}]).to_excel(writer, sheet_name="dae_constraints", index=False)
            pd.DataFrame([{"status": "not_run"}]).to_excel(writer, sheet_name="state_invariants", index=False)
            pd.DataFrame([{"status": "not_run"}]).to_excel(writer, sheet_name="dyn_resid_feedback_status", index=False)
        constrained_windows_dataframe().to_excel(writer, sheet_name="residual_aware_optimization", index=False)
        residual_aware_optimizer_dataframe(build_flowsheet_residual_system(result)).to_excel(writer, sheet_name="residual_aware_optimizer", index=False)
        residual_constrained_fit_dataframe().to_excel(writer, sheet_name="residual_aware_calibration", index=False)
        residual_aware_decision_dataframe(build_flowsheet_residual_system(result)).to_excel(writer, sheet_name="residual_aware_decision", index=False)
        posterior_residual_filter_dataframe(
            posterior.samples if posterior is not None else None,
            build_flowsheet_residual_system(result) if posterior is not None else None,
        ).to_excel(writer, sheet_name="residual_aware_posterior", index=False)
        residual_aware_doe_dataframe(build_flowsheet_residual_system(result)).to_excel(writer, sheet_name="residual_aware_doe", index=False)
        residual_aware_sampling_dataframe(result_or_system=build_flowsheet_residual_system(result)).to_excel(writer, sheet_name="residual_aware_sampling", index=False)
        residual_decision_engine_dataframe(result_or_system=build_flowsheet_residual_system(result)).to_excel(writer, sheet_name="residual_decision_engine", index=False)
        build_evidence_chain().to_excel(writer, sheet_name="evidence_chain", index=False)
        evidence_gap_dataframe().to_excel(writer, sheet_name="evidence_gaps", index=False)
        evidence_chain_score_dataframe().to_excel(writer, sheet_name="evidence_chain_score", index=False)
        evidence_gap_priority_dataframe().to_excel(writer, sheet_name="evidence_gap_priority", index=False)
        confidence_certificate_dataframe(residual_system=build_flowsheet_residual_system(result), model_outputs=result.kpis).to_excel(writer, sheet_name="confidence_certificate", index=False)
        governance_certificate_dataframe(result).to_excel(writer, sheet_name="governance_certificate", index=False)
        validation_data_upgrade_plan().to_excel(writer, sheet_name="validation_upgrade_plan", index=False)
        pd.DataFrame(
            [
                {
                    "version": "V6.4 / 0.7.4",
                    "audit_scope": "nonlinear residual loop, solve path integrator, industrial data package, benchmark reconciliation, property runtime audit, adaptive integrator, event localization, residual decision engine, governance certificate",
                    "heavy_tasks_rerun": False,
                }
            ]
        ).to_excel(writer, sheet_name="V6_4_audit_summary", index=False)
        pd.DataFrame(
            [
                {
                    "version": "V6.3 / 0.7.3",
                    "audit_scope": "equation-oriented solver, data assimilation, property runtime context, adaptive step control, residual-aware sampling, confidence certificate",
                    "heavy_tasks_rerun": False,
                }
            ]
        ).to_excel(writer, sheet_name="V6_3_audit_summary", index=False)
        pd.DataFrame(
            [
                {
                    "version": "V6.2 / 0.7.2",
                    "audit_scope": "conservation solve path, property runtime, dynamic solver policy, residual-aware optimizer/DOE, evidence chain score",
                    "heavy_tasks_rerun": False,
                }
            ]
        ).to_excel(writer, sheet_name="V6_2_audit_summary", index=False)
        ui_actions_dataframe().to_excel(writer, sheet_name="ui_task_governance", index=False)
        contracts_dataframe().to_excel(writer, sheet_name="model_contracts", index=False)
        pd.DataFrame.from_dict(load_target_grades(), orient="index").reset_index(names="grade_id").to_excel(
            writer, sheet_name="vistalon benchmarks", index=False
        )
        if sensitivity_df is not None and not sensitivity_df.empty:
            sensitivity_df.to_excel(writer, sheet_name="sensitivity", index=False)
        if optimization is not None:
            pd.DataFrame([optimization.kpis]).drop(columns=["recommendations"], errors="ignore").to_excel(
                writer, sheet_name="optimization", index=False
            )
        if calibration is not None:
            calibration.params_dataframe().to_excel(writer, sheet_name="calibration params", index=False)
            calibration.metrics_dataframe().to_excel(writer, sheet_name="calibration metrics", index=False)
            calibration.residuals.to_excel(writer, sheet_name="calibration residuals", index=False)
        if doe_df is not None and not doe_df.empty:
            doe_df.to_excel(writer, sheet_name="DOE recommendations", index=False)
        if scaleup_df is not None and not scaleup_df.empty:
            scaleup_df.to_excel(writer, sheet_name="scaleup", index=False)
        if experiment_data is not None and not experiment_data.empty:
            experiment_data.to_excel(writer, sheet_name="experiment_data", index=False)
        if data_quality is not None:
            data_quality.as_dataframe().to_excel(writer, sheet_name="data_quality", index=False)
        if parameter_sets_df is not None and not parameter_sets_df.empty:
            parameter_sets_df.to_excel(writer, sheet_name="parameter_sets", index=False)
        if parameter_estimation is not None:
            parameter_estimation.params_dataframe().to_excel(writer, sheet_name="parameter_estimation", index=False)
            parameter_estimation.train_test_metrics.to_excel(writer, sheet_name="parameter_train_test", index=False)
        if dynamic_semibatch_df is not None and not dynamic_semibatch_df.empty:
            dynamic_semibatch_df.to_excel(writer, sheet_name="dynamic_semibatch", index=False)
        if case_comparison is not None and not case_comparison.empty:
            case_comparison.to_excel(writer, sheet_name="case_comparison", index=False)
        recycle = recycle_solver or getattr(result, "recycle_solver", None)
        if recycle is not None:
            recycle.as_dataframe().to_excel(writer, sheet_name="recycle_solver", index=False)
            recycle.history.to_excel(writer, sheet_name="recycle_history", index=False)
        if safety is not None:
            safety.as_dataframe().to_excel(writer, sheet_name="safety", index=False)
        if pareto_df is not None and not pareto_df.empty:
            pareto_df.to_excel(writer, sheet_name="pareto_frontier", index=False)
        if uncertainty is not None:
            uncertainty.as_dataframe().to_excel(writer, sheet_name="uncertainty", index=False)
            pd.DataFrame([uncertainty.risk_probabilities]).to_excel(writer, sheet_name="uncertainty_risk", index=False)
            uncertainty.tornado.to_excel(writer, sheet_name="uncertainty_tornado", index=False)
        elif model_confidence is not None:
            (model_confidence if isinstance(model_confidence, pd.DataFrame) else pd.DataFrame([model_confidence])).to_excel(writer, sheet_name="model_confidence_user", index=False)
        if recipe_df is not None and not recipe_df.empty:
            recipe_df.to_excel(writer, sheet_name="recipe", index=False)
        if task_log is not None and not task_log.empty:
            task_log.to_excel(writer, sheet_name="task_log", index=False)
        if manifest is not None:
            pd.DataFrame([manifest]).to_excel(writer, sheet_name="manifest", index=False)
    return buffer.getvalue()
