"""Unified input/output schema metadata for core models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class ModelInputSpec:
    """One model input field specification."""

    name: str
    unit: str
    dtype: str = "float"
    min_value: float | None = None
    max_value: float | None = None
    required: bool = True
    description: str = ""


@dataclass(frozen=True)
class ModelOutputSpec:
    """One model output field specification."""

    name: str
    unit: str
    dtype: str = "float"
    physical_bounds: tuple[float | None, float | None] = (None, None)
    description: str = ""


@dataclass(frozen=True)
class ModelIOSchema:
    """Model IO schema used by registry, reports and UI diagnostics."""

    model_id: str
    inputs: list[ModelInputSpec] = field(default_factory=list)
    outputs: list[ModelOutputSpec] = field(default_factory=list)


def _i(name: str, unit: str, description: str = "", min_value: float | None = None, max_value: float | None = None) -> ModelInputSpec:
    return ModelInputSpec(name=name, unit=unit, min_value=min_value, max_value=max_value, description=description)


def _o(name: str, unit: str, description: str = "", low: float | None = None, high: float | None = None) -> ModelOutputSpec:
    return ModelOutputSpec(name=name, unit=unit, physical_bounds=(low, high), description=description)


SCHEMAS: dict[str, ModelIOSchema] = {
    "flowsheet": ModelIOSchema(
        "flowsheet",
        inputs=[
            _i("temperature_C", "degC", "reactor temperature", -273.15),
            _i("pressure_MPa", "MPa", "reactor pressure", 0.0),
            _i("feed_flows", "kg/h", "monomer/solvent feed rates", 0.0),
            _i("parameter_set_id", "-", "kinetic parameter set"),
        ],
        outputs=[
            _o("polymer_kg_h", "kg/h", "polymer production rate", 0.0),
            _o("mass_balance_error_pct", "%", "overall closure error"),
            _o("kpis", "-", "process KPI dictionary"),
        ],
    ),
    "template_config": ModelIOSchema(
        "template_config",
        inputs=[
            _i("template_id", "-", "reaction template identifier"),
            _i("monomer_feeds_kg_h", "kg/h", "template monomer feed map", 0.0),
            _i("chain_transfer_feeds", "kg/h or g/h", "chain-transfer feed map", 0.0),
        ],
        outputs=[
            _o("TemplateProcessConfig", "-", "template-native config object"),
            _o("feed_stream", "kg/h,mol/h", "template feed stream", 0.0),
            _o("EPDM aliases", "kg/h", "legacy EPDM shortcut feeds", 0.0),
        ],
    ),
    "template_flowsheet": ModelIOSchema(
        "template_flowsheet",
        inputs=[
            _i("TemplateProcessConfig", "-", "template-native process config"),
            _i("reaction_template", "-", "monomers, segments, MW and deltaH"),
        ],
        outputs=[
            _o("template_kpis", "mixed", "template KPI list"),
            _o("application_kpis", "mixed", "application adapter KPI dict"),
            _o("mass_balance_error", "%", "template mass balance closure"),
        ],
    ),
    "template_ode_rhs": ModelIOSchema(
        "template_ode_rhs",
        inputs=[
            _i("state_vector", "mol,kg,K,Pa", "template dynamic reactor state"),
            _i("template", "-", "reaction template"),
            _i("kinetic_parameters", "mixed", "apparent kinetic parameters"),
        ],
        outputs=[
            _o("dy_dt", "state/min", "template ODE derivative"),
            _o("dynamic_profile", "table", "bounded dynamic profile"),
            _o("solver_diagnostics", "-", "solve_ivp/fallback diagnostics"),
        ],
    ),
    "thermo_flash": ModelIOSchema(
        "thermo_flash",
        inputs=[_i("T", "K", "flash temperature", 0.0), _i("P", "Pa", "flash pressure", 0.0), _i("z_i", "mol fraction", "feed composition", 0.0, 1.0)],
        outputs=[_o("vapor_fraction", "fraction", "Rachford-Rice vapor fraction", 0.0, 1.0), _o("K_i", "-", "phase-equilibrium K values", 0.0)],
    ),
    "eos": ModelIOSchema(
        "eos",
        inputs=[_i("T", "K", "EOS temperature", 0.0), _i("P", "Pa", "EOS pressure", 0.0), _i("composition", "mol fraction", "mixture composition", 0.0, 1.0)],
        outputs=[_o("Z", "-", "compressibility factor", 0.0), _o("phi", "-", "fugacity coefficient", 0.0), _o("K_i", "-", "EOS K values", 0.0)],
    ),
    "henry_solubility": ModelIOSchema(
        "henry_solubility",
        inputs=[_i("gas_y_i", "mol fraction", "gas composition", 0.0, 1.0), _i("pressure_MPa", "MPa", "partial pressure basis", 0.0), _i("temperature_K", "K", "solution temperature", 0.0)],
        outputs=[_o("Cstar", "mol/L", "liquid saturation concentration", 0.0)],
    ),
    "reactor_kinetics": ModelIOSchema(
        "reactor_kinetics",
        inputs=[_i("C_monomer", "mol/L", "liquid monomer concentration", 0.0), _i("Cstar", "mol/L", "active center concentration", 0.0), _i("tau", "h", "residence time", 0.0)],
        outputs=[_o("conversion", "%", "monomer conversion", 0.0, 100.0), _o("polymer_kg_h", "kg/h", "polymer rate", 0.0), _o("composition_wt", "wt%", "E/P/D composition", 0.0, 100.0)],
    ),
    "dynamic_semibatch_ode": ModelIOSchema(
        "dynamic_semibatch_ode",
        inputs=[_i("recipe", "-", "batch/semi-batch recipe"), _i("initial_state", "mixed", "ODE initial inventory"), _i("t_span", "min", "simulation horizon", 0.0)],
        outputs=[_o("T_profile", "K", "temperature trajectory", 0.0), _o("conversion_profile", "%", "conversion trajectory", 0.0, 100.0), _o("event_log", "-", "recipe events")],
    ),
    "heat_balance": ModelIOSchema(
        "heat_balance",
        inputs=[_i("mol_consumed", "mol/h", "monomer consumption", 0.0), _i("deltaH", "kJ/mol", "heat of polymerization"), _i("U_A", "W/K", "heat removal UA", 0.0)],
        outputs=[_o("Q_rxn", "kW", "positive heat removal demand", 0.0), _o("deltaT_ad", "K", "adiabatic temperature rise", 0.0), _o("cooling_margin", "kW", "Qmax-Qrxn")],
    ),
    "fluid_rheology_hydraulics": ModelIOSchema(
        "fluid_rheology_hydraulics",
        inputs=[_i("solids_wt", "wt%", "polymer solids", 0.0, 100.0), _i("Mw", "g/mol", "weight average molecular weight", 0.0), _i("pipe_D", "m", "pipe diameter", 0.0)],
        outputs=[_o("viscosity", "Pa*s", "dynamic viscosity", 0.0), _o("pressure_drop", "kPa", "pipe pressure drop", 0.0), _o("pump_power", "kW", "pump power", 0.0)],
    ),
    "flash": ModelIOSchema(
        "flash",
        inputs=[_i("inlet_stream", "kg/h,mol/h", "flash inlet stream"), _i("T", "K", "flash temperature", 0.0), _i("P", "Pa", "flash pressure", 0.0)],
        outputs=[_o("vapor_stream", "kg/h", "vapor outlet", 0.0), _o("liquid_stream", "kg/h", "liquid outlet", 0.0), _o("vapor_fraction", "fraction", "vapor split", 0.0, 1.0)],
    ),
    "recycle_solver": ModelIOSchema(
        "recycle_solver",
        inputs=[_i("purge_fraction", "fraction", "purge split", 0.0, 1.0), _i("flash_recoveries", "kg/h", "recycle candidates", 0.0)],
        outputs=[_o("closure_error", "kg/h", "tear closure error", 0.0), _o("monomer_recovery", "%", "monomer recovery", 0.0, 100.0)],
    ),
    "product_properties": ModelIOSchema(
        "product_properties",
        inputs=[_i("Mw", "g/mol", "molecular weight", 0.0), _i("PDI", "-", "polydispersity", 0.0), _i("composition", "wt%", "polymer composition", 0.0, 100.0)],
        outputs=[_o("Mooney", "ML(1+4)", "Mooney viscosity", 0.0), _o("Tg", "degC", "glass transition"), _o("Tm", "degC", "melting peak estimate")],
    ),
    "parameter_estimation": ModelIOSchema(
        "parameter_estimation",
        inputs=[_i("experiment_data", "table", "calibration data"), _i("bounds", "-", "parameter bounds"), _i("weights", "-", "target weights")],
        outputs=[_o("fitted_params", "-", "estimated parameter set"), _o("mae", "target units", "mean absolute error", 0.0), _o("r2", "-", "fit score")],
    ),
    "cfd_simple": ModelIOSchema(
        "cfd_simple",
        inputs=[_i("geometry", "m", "pipe/reactor mesh dimensions", 0.0), _i("fluid_properties", "SI", "rho/mu/Cp/k"), _i("source_terms", "SI", "heat and scalar source terms")],
        outputs=[_o("temperature_field", "K", "2D temperature field", 0.0), _o("velocity_field", "m/s", "2D velocity field"), _o("fouling_index", "-", "risk index", 0.0)],
    ),
    "optimizer_pareto": ModelIOSchema(
        "optimizer_pareto",
        inputs=[_i("decision_variables", "mixed", "process variables"), _i("constraints", "mixed", "engineering constraints")],
        outputs=[_o("pareto_table", "table", "feasible process windows"), _o("objective_score", "-", "optimization objective")],
    ),
    "uncertainty": ModelIOSchema(
        "uncertainty",
        inputs=[_i("uncertain_parameters", "% or absolute", "parameter perturbations"), _i("n_samples", "count", "sample count", 1.0)],
        outputs=[_o("confidence_interval", "KPI units", "KPI intervals"), _o("risk_probability", "fraction", "risk probability", 0.0, 1.0)],
    ),
    "data_case_report": ModelIOSchema(
        "data_case_report",
        inputs=[_i("results_store", "-", "existing simulation results"), _i("report_options", "-", "report export options")],
        outputs=[_o("excel_report", "file", "Excel artifact"), _o("word_report", "file", "Word artifact")],
    ),
    "model_governance_v43": ModelIOSchema(
        "model_governance_v43",
        inputs=[_i("flowsheet_result", "-", "existing fast result"), _i("model_registry", "-", "registered models"), _i("task_log", "-", "TaskService records")],
        outputs=[_o("conservation_results", "table", "mass/energy closure checks"), _o("engineering_rule_results", "table", "trend-rule results"), _o("model_confidence_card", "score", "0-100 confidence score", 0.0, 100.0)],
    ),
    "equation_code_consistency": ModelIOSchema(
        "equation_code_consistency",
        inputs=[_i("equation_registry", "-", "registered equations"), _i("core_functions", "-", "callable model functions")],
        outputs=[_o("check_table", "table", "equation-code trend checks"), _o("failed_count", "count", "failed checks", 0.0)],
    ),
    "report": ModelIOSchema(
        "report",
        inputs=[_i("result", "-", "precomputed result object"), _i("figures", "-", "optional static figures")],
        outputs=[_o("xlsx_bytes", "bytes", "Excel report"), _o("docx_bytes", "bytes", "Word report")],
    ),
    "openfoam_export": ModelIOSchema(
        "openfoam_export",
        inputs=[_i("geometry", "m", "mesh geometry"), _i("boundary_conditions", "SI", "OpenFOAM boundary conditions")],
        outputs=[_o("case_zip", "file", "OpenFOAM case package")],
    ),
    "residual_objective": ModelIOSchema(
        "residual_objective",
        inputs=[_i("residual_system", "registered residual units", "flowsheet/dynamic residual bundle")],
        outputs=[_o("residual_objective_score", "score", "optimizer/DOE residual penalty", 0.0), _o("rejected", "boolean", "critical residual rejection flag")],
    ),
    "dynamic_residuals": ModelIOSchema(
        "dynamic_residuals",
        inputs=[_i("dynamic_profile", "min,kg,Pa,K,mol/h", "precomputed dynamic ODE profile")],
        outputs=[_o("dynamic_residual_table", "table", "time-resolved residual diagnostics"), _o("dynamic_residual_acceptance", "-", "pass/fail summary")],
    ),
    "phase_equilibrium_constraints": ModelIOSchema(
        "phase_equilibrium_constraints",
        inputs=[_i("flash_result", "kg/h,mol/h", "precomputed flash result"), _i("T", "K", "temperature", 0.0), _i("P", "Pa", "pressure", 0.0)],
        outputs=[_o("constraint_table", "table", "EOS/K/flash physical constraints"), _o("flash_residuals", "table", "RR and split residuals")],
    ),
    "experimental_benchmark": ModelIOSchema(
        "experimental_benchmark",
        inputs=[_i("experimental_benchmarks", "json", "benchmark metadata file")],
        outputs=[_o("benchmark_acceptance", "table", "accepted benchmark metadata"), _o("benchmark_confidence_score", "score", "0-100 source confidence", 0.0, 100.0)],
    ),
    "residual_solver": ModelIOSchema(
        "residual_solver",
        inputs=[_i("ResidualSystem", "registered residual units", "mass/energy/phase residual bundle")],
        outputs=[_o("weighted_objective", "score", "residual-driven objective penalty", 0.0), _o("correction_trace", "table", "bounded correction trace")],
    ),
    "benchmark_calibration": ModelIOSchema(
        "benchmark_calibration",
        inputs=[_i("experimental_benchmarks", "json", "experiment/literature/plant/synthetic benchmark file"), _i("model_outputs", "KPI units", "precomputed model outputs")],
        outputs=[_o("benchmark_residuals", "table", "weighted benchmark residual table"), _o("data_gap_recommendations", "table", "next calibration data suggestions")],
    ),
    "dynamic_rhs_residual_coupling": ModelIOSchema(
        "dynamic_rhs_residual_coupling",
        inputs=[_i("dynamic_profile", "min,kg,Pa,K,mol/h", "precomputed dynamic profile"), _i("rhs_terms", "state/min", "RHS derivative term table")],
        outputs=[_o("rhs_residual_acceptance", "-", "RHS/residual coupling status"), _o("residual_timeseries", "table", "dynamic residual time series")],
    ),
    "data_lineage": ModelIOSchema(
        "data_lineage",
        inputs=[_i("benchmark_or_dataset_metadata", "json", "benchmark/calibration provenance metadata")],
        outputs=[_o("lineage_table", "table", "source/unit/hash/validity lineage"), _o("lineage_confidence_score", "score", "0-100 data provenance score", 0.0, 100.0)],
    ),
    "residual_constrained_fit": ModelIOSchema(
        "residual_constrained_fit",
        inputs=[_i("target_data", "target units", "endpoint/time-series calibration data"), _i("ResidualSystem", "registered residual units", "physical residual bundle"), _i("parameter_bounds", "mixed", "parameter constraints")],
        outputs=[_o("objective", "score", "data + physical residual objective", 0.0), _o("accepted", "boolean", "calibrated-set acceptance flag")],
    ),
    "posterior_residual_filter": ModelIOSchema(
        "posterior_residual_filter",
        inputs=[_i("posterior_samples", "parameter units", "bounded posterior sample table"), _i("ResidualSystem", "registered residual units", "physical residual bundle")],
        outputs=[_o("residual_acceptance_rate", "fraction", "accepted posterior sample fraction", 0.0, 1.0), _o("sample_filter_table", "table", "sample-level residual acceptance")],
    ),
    "equation_reverse_check": ModelIOSchema(
        "equation_reverse_check",
        inputs=[_i("equation_registry", "json", "registered executable equations"), _i("implementation_functions", "callables", "bound code implementations")],
        outputs=[_o("reverse_check_table", "table", "code-to-registry consistency checks"), _o("failed_count", "count", "critical reverse check failures", 0.0)],
    ),
    "dynamic_residual_feedback": ModelIOSchema(
        "dynamic_residual_feedback",
        inputs=[_i("dynamic_profile", "min,kg,Pa,K,mol/h", "precomputed dynamic ODE profile")],
        outputs=[_o("residual_acceptance_rate", "fraction", "dynamic residual acceptance", 0.0, 1.0), _o("solver_warning", "boolean", "fallback/warning recommendation")],
    ),
    "calibrated_property_models": ModelIOSchema(
        "calibrated_property_models",
        inputs=[_i("property_calibration_result", "dataset units", "Henry/viscosity/flash/deltaH calibration result")],
        outputs=[_o("calibrated_property_set", "json", "saved property model with lineage"), _o("confidence_score", "score", "0-100 calibrated property score", 0.0, 100.0)],
    ),
    "equation_residual_coupling": ModelIOSchema(
        "equation_residual_coupling",
        inputs=[_i("equation_registry", "json", "critical equation metadata"), _i("ResidualSystem", "registered residual units", "residual metadata")],
        outputs=[_o("coupling_table", "table", "equation-code-residual-benchmark coupling"), _o("failed_count", "count", "failed coupling rows", 0.0)],
    ),
    "residual_acceptance": ModelIOSchema(
        "residual_acceptance",
        inputs=[_i("ResidualSystem", "registered residual units", "physical residual bundle")],
        outputs=[_o("acceptance_table", "table", "calibration/optimizer/DOE/posterior acceptance"), _o("residual_objective_score", "score", "acceptance penalty", 0.0)],
    ),
    "dynamic_stability_checks": ModelIOSchema(
        "dynamic_stability_checks",
        inputs=[_i("dynamic_profile", "min,kg,Pa,K,mol/h", "precomputed dynamic ODE profile")],
        outputs=[_o("stability_table", "table", "proof-style dynamic stability checks"), _o("stiffness_indicator", "-", "profile gradient proxy", 0.0)],
    ),
    "benchmark_source_registry": ModelIOSchema(
        "benchmark_source_registry",
        inputs=[_i("benchmark_sources", "json", "benchmark source registry")],
        outputs=[_o("source_registry_table", "table", "source lineage confidence table"), _o("critical_release_allowed", "boolean", "release-gate source eligibility")],
    ),
    "calibrated_property_usage": ModelIOSchema(
        "calibrated_property_usage",
        inputs=[_i("calibrated_property_models", "json", "saved calibrated property model records"), _i("conditions", "SI/project units", "current model conditions")],
        outputs=[_o("usage_table", "table", "selected calibrated/default property usage"), _o("confidence_score", "score", "selected model confidence", 0.0, 100.0)],
    ),
    "math_core": ModelIOSchema(
        "math_core",
        inputs=[_i("equations_residuals_constraints", "mixed", "registered equation, residual and constraint metadata")],
        outputs=[_o("math_core_acceptance", "boolean", "combined math-core acceptance"), _o("diagnostics", "table", "layered math-core diagnostics")],
    ),
    "solver_core": ModelIOSchema(
        "solver_core",
        inputs=[_i("state_vector", "state units", "bounded solver state"), _i("ResidualSystem", "registered residual units", "residual quality")],
        outputs=[_o("solver_status", "table", "residual-aware solver status"), _o("fallback_recommended", "boolean", "fallback recommendation")],
    ),
    "model_traceability_graph": ModelIOSchema(
        "model_traceability_graph",
        inputs=[_i("equation_registry", "json", "equation metadata"), _i("ResidualSystem", "registered residual units", "residual metadata"), _i("data_lineage", "json/table", "benchmark lineage")],
        outputs=[_o("traceability_table", "table", "equation-residual-benchmark-lineage traceability"), _o("failed_links", "count", "missing critical links", 0.0)],
    ),
    "constrained_solver": ModelIOSchema(
        "constrained_solver",
        inputs=[_i("ResidualSystem", "registered residual units", "mass/energy/phase residuals"), _i("bounds", "mixed", "physical solver bounds")],
        outputs=[_o("solver_certificate", "table", "residual norm and constraint violations"), _o("accepted", "boolean", "constraint acceptance")],
    ),
    "dae_state_invariants": ModelIOSchema(
        "dae_state_invariants",
        inputs=[_i("dynamic_profile", "min,kg,Pa,K,mol", "precomputed dynamic profile")],
        outputs=[_o("dae_constraints", "table", "algebraic state constraints"), _o("state_invariants", "table", "monotonicity/positivity checks")],
    ),
    "model_confidence_engine": ModelIOSchema(
        "model_confidence_engine",
        inputs=[_i("validation_evidence", "table", "benchmark/data-lineage evidence"), _i("ResidualSystem", "registered residual units", "residual acceptance")],
        outputs=[_o("overall_score", "score", "evidence-weighted confidence", 0.0, 100.0), _o("confidence_decomposition", "table", "component scores")],
    ),
    "property_model_selector": ModelIOSchema(
        "property_model_selector",
        inputs=[_i("calibrated_property_models", "json/table", "saved calibrated/default property models"), _i("conditions", "project units", "T/P/composition validity conditions")],
        outputs=[_o("selected_model", "table", "chosen property model and confidence"), _o("within_validity", "boolean", "validity flag")],
    ),
}


def load_io_schemas() -> dict[str, ModelIOSchema]:
    """Return all built-in IO schemas."""
    return dict(SCHEMAS)


def get_io_schema(model_id: str) -> ModelIOSchema:
    """Return one IO schema by model id."""
    return SCHEMAS[model_id]


def io_schema_dataframe(schemas: dict[str, ModelIOSchema] | None = None) -> pd.DataFrame:
    """Return a flattened IO schema table."""
    schemas = load_io_schemas() if schemas is None else schemas
    rows: list[dict[str, Any]] = []
    for model_id, schema in schemas.items():
        for item in schema.inputs:
            rows.append(
                {
                    "model_id": model_id,
                    "direction": "input",
                    "name": item.name,
                    "unit": item.unit,
                    "dtype": item.dtype,
                    "min": item.min_value,
                    "max": item.max_value,
                    "required": item.required,
                    "description": item.description,
                }
            )
        for item in schema.outputs:
            rows.append(
                {
                    "model_id": model_id,
                    "direction": "output",
                    "name": item.name,
                    "unit": item.unit,
                    "dtype": item.dtype,
                    "min": item.physical_bounds[0],
                    "max": item.physical_bounds[1],
                    "required": True,
                    "description": item.description,
                }
            )
    return pd.DataFrame(rows)
