"""Audit-grade reproducibility package export/import."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any
import hashlib
import json
import platform
import sys
import zipfile

import pandas as pd

from .conservation import conservation_dataframe, run_conservation_checks
from .engineering_rules import rules_dataframe
from .equation_registry import equation_registry_dataframe
from .kpi_adapter import build_template_kpis
from .kpi_schema import kpis_to_dataframe
from .model_audit_report import build_model_audit_report
from .model_registry import module_trigger_dataframe
from .reaction_templates import get_reaction_template
from .utils import model_dump_compat
from .audit_trail import AuditTrailRecord, audit_trail_dataframe, create_audit_record
from .file_security import export_metadata
from .residual_system import build_flowsheet_residual_system, residual_system_dataframe
from .scientific_benchmarks import benchmark_definitions
from .experimental_benchmark import experimental_benchmarks_dataframe
from .benchmark_calibration import benchmark_residual_dataframe, recommend_calibration_data_gaps
from .calibrated_property_models import calibrated_property_models_dataframe, calibrated_property_usage_dataframe
from .data_lineage import data_lineage_dataframe
from .equation_reverse_check import run_equation_reverse_checks
from .equation_residual_coupling import equation_residual_coupling_dataframe
from .residual_acceptance import residual_acceptance_dataframe
from .benchmark_source_registry import benchmark_lineage_dataframe, benchmark_source_registry_dataframe
from .data_lineage_graph import build_data_lineage_graph
from .dimensioned import unit_conversion_trace_dataframe
from .model_graph import build_equation_graph, model_traceability_dataframe
from .model_confidence_engine import confidence_decomposition, validation_evidence_dataframe
from .property_model_selector import property_model_selection_dataframe
from .property_model_bridge import property_model_bridge_dataframe
from .property_model_runtime import property_model_runtime_dataframe
from .property_runtime_context import property_runtime_context_dataframe
from .property_runtime_audit import property_runtime_audit_dataframe
from .residual_graph import build_residual_graph
from .residual_solver import residual_correction_trace_dataframe
from .residual_aware_decision import residual_aware_decision_dataframe
from .residual_aware_doe import residual_aware_doe_dataframe
from .residual_aware_optimizer import residual_aware_optimizer_dataframe
from .residual_aware_sampling import residual_aware_sampling_dataframe
from .residual_aware_decision_engine import residual_decision_engine_dataframe
from .solver_core.solver_certificates import solver_certificate_dataframe
from .solver_core.conservation_correction import correction_certificate_dataframe
from .solver_core.conservation_solve_path import conservation_solve_certificate_dataframe
from .solver_core.conservation_jacobian import conservation_jacobian_dataframe
from .solver_core.equation_oriented_solver import equation_oriented_solver_certificate
from .solver_core.nonlinear_residual_loop import residual_iteration_certificate
from .solver_core.solve_path_integrator import solve_path_integrator_dataframe
from .dynamic_core.solver_decision import dynamic_solver_decision_dataframe
from .dynamic_core.solver_policy import dynamic_solver_policy_dataframe
from .dynamic_core.step_acceptance import dynamic_step_acceptance_dataframe
from .dynamic_core.adaptive_step_control import adaptive_step_control_dataframe
from .dynamic_core.event_detection import dynamic_event_detection_dataframe
from .dynamic_core.adaptive_integrator import adaptive_integrator_dataframe
from .dynamic_core.event_localization import event_localization_dataframe
from .evidence_chain import build_evidence_chain, evidence_gap_dataframe
from .evidence_chain_score import evidence_chain_score_dataframe, evidence_gap_priority_dataframe
from .data_assimilation import data_assimilation_dataframe
from .calibration_data_package import calibration_data_lineage_dataframe, calibration_package_dataframe
from .industrial_data_package import industrial_data_lineage_dataframe, industrial_data_package_dataframe
from .benchmark_reconciliation import benchmark_reconciliation_dataframe
from .model_confidence_certificate import confidence_certificate_dataframe, validation_data_upgrade_plan
from .governance_certificate import governance_certificate_dataframe


def _json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str).encode("utf-8")


def _hash_payload(payload: Any) -> str:
    return hashlib.sha1(_json_bytes(payload)).hexdigest()[:12]


@dataclass(frozen=True)
class ReproPackageManifest:
    """Manifest for a reproducible case package."""

    app_version: str
    created_at: str
    config_hash: str
    parameter_set_hash: str
    data_snapshot_hash: str
    model_registry_hash: str
    equation_registry_hash: str
    test_status: str
    generated_by: str = "metallocene-epdm-digital-twin"

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def build_repro_manifest(result: Any, *, parameter_set: dict[str, Any] | None = None, test_status: str = "not_run") -> ReproPackageManifest:
    """Build a reproducibility manifest from existing results only."""
    import datetime as _dt

    config = model_dump_compat(result.config)
    parameter_set = parameter_set or {"parameter_set_id": getattr(result.config, "parameter_set_id", "default")}
    registry_df = module_trigger_dataframe()
    equation_df = equation_registry_dataframe()
    return ReproPackageManifest(
        app_version="V6.4 / 0.7.4",
        created_at=_dt.datetime.now(_dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        config_hash=_hash_payload(config),
        parameter_set_hash=_hash_payload(parameter_set),
        data_snapshot_hash=_hash_payload({"kpis": getattr(result, "kpis", {})}),
        model_registry_hash=_hash_payload(registry_df.to_dict(orient="records")),
        equation_registry_hash=_hash_payload(equation_df.to_dict(orient="records")),
        test_status=test_status,
    )


def export_repro_package(
    result: Any,
    *,
    parameter_set: dict[str, Any] | None = None,
    report_xlsx: bytes | None = None,
    report_docx: bytes | None = None,
    test_status: str = "not_run",
    audit_records: list[AuditTrailRecord] | None = None,
) -> bytes:
    """Export a zip package with enough metadata to reproduce the case."""
    buffer = BytesIO()
    manifest = build_repro_manifest(result, parameter_set=parameter_set, test_status=test_status)
    template = get_reaction_template("EPDM_EPM_metallocene_solution")
    kpi_df = kpis_to_dataframe(build_template_kpis(template.template_id, result))
    audit = build_model_audit_report(result)
    audit_records = audit_records or [
        create_audit_record(
            "export_repro_package",
            "repro_package_export",
            model_dump_compat(result.config),
            {"manifest": manifest.as_dict()},
            parameter_set_id=getattr(result.config, "parameter_set_id", "default"),
            template_id="EPDM_EPM_metallocene_solution",
            status="success",
        )
    ]
    env = {
        "python": sys.version,
        "platform": platform.platform(),
        "executable": sys.executable,
    }
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", _json_bytes(manifest.as_dict()))
        zf.writestr(
            "export_metadata.json",
            _json_bytes(
                export_metadata(
                    version=manifest.app_version,
                    config=model_dump_compat(result.config),
                    parameter_set_id=str((parameter_set or {}).get("parameter_set_id", getattr(result.config, "parameter_set_id", "default"))),
                    template_id=template.template_id,
                    model_registry=module_trigger_dataframe().to_dict(orient="records"),
                    equation_registry=equation_registry_dataframe().to_dict(orient="records"),
                    warnings=list(getattr(result, "warnings", [])),
                    missing_heavy_tasks=["dynamic_ode", "cfd", "optimization", "posterior", "doe"],
                )
            ),
        )
        zf.writestr("config.json", _json_bytes(model_dump_compat(result.config)))
        zf.writestr("parameter_set.json", _json_bytes(parameter_set or {"parameter_set_id": getattr(result.config, "parameter_set_id", "default")}))
        zf.writestr("reaction_template.json", _json_bytes(template.__dict__))
        zf.writestr("model_registry_snapshot.json", module_trigger_dataframe().to_json(orient="records", force_ascii=False))
        zf.writestr("equation_registry_snapshot.json", equation_registry_dataframe().to_json(orient="records", force_ascii=False))
        zf.writestr("benchmark_snapshot.json", benchmark_definitions().to_json(orient="records", force_ascii=False))
        zf.writestr("experimental_benchmarks.json", experimental_benchmarks_dataframe().to_json(orient="records", force_ascii=False))
        zf.writestr("data_lineage.csv", data_lineage_dataframe().to_csv(index=False))
        zf.writestr("data_lineage_graph.csv", build_data_lineage_graph().to_csv(index=False))
        zf.writestr("benchmark_sources.csv", benchmark_source_registry_dataframe().to_csv(index=False))
        zf.writestr("benchmark_lineage.csv", benchmark_lineage_dataframe().to_csv(index=False))
        zf.writestr("model_traceability_graph.csv", model_traceability_dataframe().to_csv(index=False))
        zf.writestr("equation_graph.csv", build_equation_graph().to_csv(index=False))
        zf.writestr("residual_graph.csv", build_residual_graph(build_flowsheet_residual_system(result)).to_csv(index=False))
        zf.writestr("equation_reverse_check.csv", run_equation_reverse_checks().to_csv(index=False))
        zf.writestr("equation_residual_coupling.csv", equation_residual_coupling_dataframe().to_csv(index=False))
        zf.writestr("calibrated_property_models.csv", calibrated_property_models_dataframe().to_csv(index=False))
        zf.writestr("calibrated_property_usage.csv", calibrated_property_usage_dataframe().to_csv(index=False))
        zf.writestr("property_model_selection.csv", property_model_selection_dataframe().to_csv(index=False))
        zf.writestr("property_model_bridge.csv", property_model_bridge_dataframe().to_csv(index=False))
        zf.writestr("property_model_runtime.csv", property_model_runtime_dataframe().to_csv(index=False))
        zf.writestr("property_runtime_context.csv", property_runtime_context_dataframe(result).to_csv(index=False))
        zf.writestr("property_runtime_audit.csv", property_runtime_audit_dataframe(result).to_csv(index=False))
        zf.writestr("calibration_data_package.csv", calibration_package_dataframe().to_csv(index=False))
        zf.writestr("calibration_data_lineage.csv", calibration_data_lineage_dataframe().to_csv(index=False))
        zf.writestr("data_assimilation.csv", data_assimilation_dataframe().to_csv(index=False))
        zf.writestr("industrial_data_package.csv", industrial_data_package_dataframe().to_csv(index=False))
        zf.writestr("industrial_data_lineage.csv", industrial_data_lineage_dataframe().to_csv(index=False))
        zf.writestr("benchmark_reconciliation.csv", benchmark_reconciliation_dataframe(model_outputs=getattr(result, "kpis", {})).to_csv(index=False))
        zf.writestr("validation_evidence.csv", validation_evidence_dataframe().to_csv(index=False))
        zf.writestr("evidence_chain.csv", build_evidence_chain().to_csv(index=False))
        zf.writestr("evidence_gaps.csv", evidence_gap_dataframe().to_csv(index=False))
        zf.writestr("evidence_chain_score.csv", evidence_chain_score_dataframe().to_csv(index=False))
        zf.writestr("evidence_gap_priority.csv", evidence_gap_priority_dataframe().to_csv(index=False))
        zf.writestr("confidence_decomposition.csv", confidence_decomposition(residual_system=build_flowsheet_residual_system(result), model_outputs=getattr(result, "kpis", {})).to_csv(index=False))
        zf.writestr("solver_certificate.csv", solver_certificate_dataframe(build_flowsheet_residual_system(result)).to_csv(index=False))
        zf.writestr("correction_certificates.csv", correction_certificate_dataframe(build_flowsheet_residual_system(result)).to_csv(index=False))
        zf.writestr("conservation_solve_certificate.csv", conservation_solve_certificate_dataframe(build_flowsheet_residual_system(result)).to_csv(index=False))
        zf.writestr("equation_oriented_solver.csv", equation_oriented_solver_certificate(build_flowsheet_residual_system(result)).to_csv(index=False))
        zf.writestr("conservation_jacobian.csv", conservation_jacobian_dataframe(build_flowsheet_residual_system(result)).to_csv(index=False))
        zf.writestr("nonlinear_residual_loop.csv", residual_iteration_certificate(build_flowsheet_residual_system(result)).to_csv(index=False))
        zf.writestr("solve_path_integrator.csv", solve_path_integrator_dataframe(build_flowsheet_residual_system(result)).to_csv(index=False))
        zf.writestr("dynamic_solver_decision.csv", dynamic_solver_decision_dataframe().to_csv(index=False))
        zf.writestr("dynamic_solver_policy.csv", dynamic_solver_policy_dataframe().to_csv(index=False))
        zf.writestr("dynamic_step_acceptance.csv", dynamic_step_acceptance_dataframe().to_csv(index=False))
        zf.writestr("adaptive_step_control.csv", adaptive_step_control_dataframe().to_csv(index=False))
        zf.writestr("dynamic_event_detection.csv", dynamic_event_detection_dataframe().to_csv(index=False))
        zf.writestr("adaptive_integrator.csv", adaptive_integrator_dataframe().to_csv(index=False))
        zf.writestr("event_localization.csv", event_localization_dataframe().to_csv(index=False))
        zf.writestr("residual_aware_decision.csv", residual_aware_decision_dataframe(build_flowsheet_residual_system(result)).to_csv(index=False))
        zf.writestr("residual_aware_optimizer.csv", residual_aware_optimizer_dataframe(build_flowsheet_residual_system(result)).to_csv(index=False))
        zf.writestr("residual_aware_doe.csv", residual_aware_doe_dataframe(build_flowsheet_residual_system(result)).to_csv(index=False))
        zf.writestr("residual_aware_sampling.csv", residual_aware_sampling_dataframe(result_or_system=build_flowsheet_residual_system(result)).to_csv(index=False))
        zf.writestr("residual_decision_engine.csv", residual_decision_engine_dataframe(result_or_system=build_flowsheet_residual_system(result)).to_csv(index=False))
        zf.writestr("confidence_certificate.csv", confidence_certificate_dataframe(residual_system=build_flowsheet_residual_system(result), model_outputs=getattr(result, "kpis", {})).to_csv(index=False))
        zf.writestr("governance_certificate.csv", governance_certificate_dataframe(result).to_csv(index=False))
        zf.writestr("validation_upgrade_plan.csv", validation_data_upgrade_plan().to_csv(index=False))
        zf.writestr("benchmark_residuals.csv", benchmark_residual_dataframe(getattr(result, "kpis", {})).to_csv(index=False))
        zf.writestr("benchmark_data_gaps.csv", recommend_calibration_data_gaps(getattr(result, "kpis", {})).to_csv(index=False))
        zf.writestr("unit_conversion_trace.csv", unit_conversion_trace_dataframe().to_csv(index=False))
        zf.writestr("residual_correction_trace.csv", residual_correction_trace_dataframe().to_csv(index=False))
        zf.writestr("kpis.csv", kpi_df.to_csv(index=False))
        zf.writestr("residual_system.csv", residual_system_dataframe(build_flowsheet_residual_system(result)).to_csv(index=False))
        zf.writestr("residual_acceptance.csv", residual_acceptance_dataframe(build_flowsheet_residual_system(result)).to_csv(index=False))
        zf.writestr("conservation.csv", conservation_dataframe(run_conservation_checks(result)).to_csv(index=False))
        zf.writestr("engineering_rules.csv", rules_dataframe().to_csv(index=False))
        zf.writestr("model_audit.csv", audit.as_dataframe().to_csv(index=False))
        zf.writestr("audit_trail.csv", audit_trail_dataframe(audit_records).to_csv(index=False))
        zf.writestr("environment.txt", "\n".join(f"{key}: {value}" for key, value in env.items()))
        zf.writestr("test_snapshot.txt", test_status)
        if report_xlsx:
            zf.writestr("report.xlsx", report_xlsx)
        else:
            zf.writestr("report_status.txt", "report_xlsx not supplied; export did not rerun report generation")
        if report_docx:
            zf.writestr("report.docx", report_docx)
    return buffer.getvalue()


def load_repro_manifest_from_zip(path_or_bytes: str | Path | bytes) -> dict[str, Any]:
    """Load manifest.json from a reproducibility package."""
    if isinstance(path_or_bytes, bytes):
        handle = BytesIO(path_or_bytes)
    else:
        handle = Path(path_or_bytes)
    with zipfile.ZipFile(handle, "r") as zf:
        return json.loads(zf.read("manifest.json").decode("utf-8"))
