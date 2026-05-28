# Metallocene EPDM Digital Twin - 全量技术架构、部署与使用说明书

本文档包含该软体实现的全量功能详细技术架构说明、逐步部署指南（Step by Step）以及详细的用户使用手册。

---

## 1. 逐步部署指南 (Deployment Step by Step)

该数字孪生平台基于 Python 构建，前后端集成在 Streamlit 中，部署非常轻量。请按照以下步骤在您的计算机或服务器上运行：

### 步骤 1：准备系统环境
- 确保您的操作系统为 Windows、macOS 或 Linux。
- 安装 **Python 3.9 或更高版本**（推荐 Python 3.10 或 3.11）。
- 建议安装并使用虚拟环境工具（如 `venv` 或 `conda`）。

### 步骤 2：获取工程代码
将本项目源码文件夹 `metallocene-epdm-digital-twin` 下载或克隆至本地磁盘（如 `D:\codex\metallocene-epdm-digital-twin`）。

### 步骤 3：安装依赖
打开终端（命令提示符或 PowerShell），进入项目根目录：
```bash
cd /path/to/metallocene-epdm-digital-twin
pip install -r requirements.txt
```
*(这将会安装所需的核心库：numpy、scipy、pandas、streamlit 等)*

### 步骤 4：启动与运行系统
在当前根目录下，执行以下命令以启动系统后端服务器和前端 Web 界面：
```bash
python -m streamlit run app.py
```

### 步骤 5：访问与使用
启动成功后，控制台会输出网络地址。请打开浏览器并访问：
**http://localhost:8501** 或者 **http://127.0.0.1:8501**
此时您就可以看到平台的交互可视化控制台了。

---

## 2. 软件详细使用说明书 (User Manual)

本软件主要用于茂金属 EPM/EPDM 溶液聚合工艺的研发模拟、敏感性分析、参数校准与热安全评估。通过 Web UI 即可完成操作：

### 2.1 全局配置与模拟计算 (Sidebar Controls)
- **全局快速输入栏 (左侧导航栏)**：您可以在此直接设置**核心反应条件**。如：
  - 反应温度 (°C)
  - 反应压力 (MPa)
  - 乙烯、丙烯、ENB 和氢气进料量
  - 反应器模式（支持批次、半连续、CSTR 串联等）
- **运行模拟**：设置好参数后，点击“**运行快速流程模拟**”按钮。系统会在后台触发数理引擎，执行质量与能量守恒迭代计算。

### 2.2 核心分析视图 (Pages Navigation)
左侧栏提供了多个功能页面切换，计算完成后请切换视图进行监测与分析：
- **数字孪生总览**：查看系统的全貌、核心KPI指标（如产率、聚合度、反应放热等）。
- **釜式聚合工艺时序**：查看聚合物随时间或轴向深度的转化率与物性动态变化曲线。
- **反应器与动力学**：监测催化剂活性、聚合动力学参数。 
- **分离脱挥与回收**：查看闪蒸罐 (Flash) 的 VLE 相平衡数据、溶剂回收效率。 
- **产品性能与美孚对标**：查看聚合物宏观物性预测，并和特定标准牌号做物理对照。
- **CFD有限元可视化**：通过 3D 模型和彩色场分布查看反应器内部温度与浓度的预估分布。
- **模型治理与可信度证书**：系统自动打分，评估当前的计算残差和物理可信度（非常关键，若标红说明物理量不守恒）。

### 2.3 高级研发功能
- **参数集与非线性估计**：输入中试实验室的真实数据点，触发底层优化器反向回归模型系数。
- **报告导出**：随时在“报告导出”页面将您的运算结果生成 Excel 快照和审核报告供归档。

---

## 3. 技术架构与全量文件遍历 (Technical Architecture & Code Details)

本数字孪生工具摒弃了传统的“黑盒经验公式”，底层全部基于“非线性方程残差感知（Residual-aware Equation-oriented）”的物理化学守恒框架进行约束求解，确保在极值工况下的预测仍具备可靠性。
以下为工程底层 (`epdm_sim/`) 各子模块与其实现的核心函数与类清单：

### 文件模块: `audit_trail.py`
**技术描述**: Audit trail records for task and report reproducibility.

**核心技术类 (Classes)**:
- `AuditTrailRecord`: One reproducible action/task record.

**核心技术函数接口 (Functions)**:
- `create_audit_record()`: Create a stable audit record from task inputs and outputs.
- `audit_trail_dataframe()`: Return audit trail rows as a DataFrame.
- `save_audit_to_sqlite()`: Append audit records to the local SQLite warehouse.
- `compare_repro_package_manifest()`: Compare two reproducibility manifests by key.

---

### 文件模块: `bayesian_doe.py`
**技术描述**: Uncertainty-driven constrained DOE ranking utilities.

**核心技术类 (Classes)**:
- `CandidateExperiment`: One ranked candidate experiment.

**核心技术函数接口 (Functions)**:
- `generate_candidate_design_space()`: Generate a compact deterministic candidate design space.
- `score_candidate_by_uncertainty()`: Score a candidate by how much it excites weak/uncertain parameters.
- `score_candidate_by_engineering_feasibility()`: Run light preflight/flowsheet checks and return feasibility flags plus risk.
- `rank_bayesian_doe_candidates()`: Rank constrained DOE candidates by uncertainty information and feasibility.
- `recommend_next_experiment_batch()`: Return the top N feasible uncertainty-driven DOE candidates.

---

### 文件模块: `benchmark_calibration.py`
**技术描述**: Benchmark calibration and data-gap scoring for V5.5.

**核心技术函数接口 (Functions)**:
- `benchmark_weight_by_confidence()`: Return a 0-1 benchmark weight from source type and confidence.
- `compare_model_to_experimental_benchmark()`: Compare supplied model outputs to benchmark expected values.
- `benchmark_residual_dataframe()`: Return weighted benchmark residual rows.
- `update_model_confidence_from_benchmarks()`: Return a benchmark-adjusted confidence score.
- `recommend_calibration_data_gaps()`: Recommend next data types from benchmark coverage and failures.
- `benchmark_calibration_summary()`: Return benchmark calibration score summary.

---

### 文件模块: `benchmark_reconciliation.py`
**技术描述**: Benchmark reconciliation helpers for V6.4 industrial evidence.

**核心技术函数接口 (Functions)**:
- `estimate_measurement_uncertainty()`: Expose benchmark-level measurement uncertainty.
- `reconcile_benchmark_observations()`: Compare package observations against model outputs with uncertainty.
- `benchmark_reconciliation_dataframe()`: Return benchmark reconciliation rows.
- `benchmark_reconciliation_summary()`: Return compact reconciliation status.
- `benchmark_reconciliation_gate()`: Return release-gate status for benchmark reconciliation.

---

### 文件模块: `benchmark_source_registry.py`
**技术描述**: Benchmark source registry and lineage checks for V5.7.

**核心技术函数接口 (Functions)**:
- `load_benchmark_sources()`: Load benchmark source records, falling back to experimental benchmarks.
- `benchmark_source_registry_dataframe()`: Return benchmark sources with release-gate confidence fields.
- `benchmark_source_registry_summary()`: Return compact source-registry acceptance summary.
- `benchmark_lineage_dataframe()`: Return source rows normalized for report/repro lineage sheets.

---

### 文件模块: `calibrated_property_models.py`
**技术描述**: Calibrated property-model registry helpers for V5.6.

**核心技术类 (Classes)**:
- `CalibratedPropertyModel`: One saved/default property model with provenance.

**核心技术函数接口 (Functions)**:
- `default_property_model()`: Return a low-confidence default property model.
- `calibrated_model_from_property_result()`: Convert a property calibration result to a saveable model record.
- `save_calibrated_property_models()`: Persist calibrated property model records without modifying defaults.
- `load_calibrated_property_models()`: Load calibrated property model records.
- `calibrated_property_models_dataframe()`: Return calibrated property models as a report table.
- `calibrated_property_model_score()`: Return average property-model confidence score.
- `calibrated_property_validity_check()`: Check supplied conditions against a calibrated model validity range.
- `select_calibrated_property_model()`: Select the highest-confidence calibrated model valid for conditions.
- `apply_calibrated_property_value()`: Apply a calibrated multiplier/value to a base property with diagnostics.
- `calibrated_property_usage_dataframe()`: Return explicit usage rows for Henry, viscosity, flash-K and deltaH paths.

---

### 文件模块: `calibration.py`
**技术描述**: Experiment-data calibration and DOE utilities for the EPDM digital twin.

**核心技术类 (Classes)**:
- `CalibrationResult`: Calibration output for kinetics, product properties and diagnostics.

**核心技术函数接口 (Functions)**:
- `load_catalysts()`: Load catalyst knowledge records extracted from project and PDF rules.
- `catalyst_dataframe()`: Return catalyst knowledge records as a flat DataFrame for UI display.
- `pdf_rules_dataframe()`: Return the research-summary rules as a two-column table.
- `calibrate_from_internal_data()`: Calibrate apparent parameters and empirical prediction residuals.
- `recommend_doe()`: Recommend a compact next-experiment DOE matrix based on PDF rules.
- `hydrogen_tuning_recommendation()`: Recommend hydrogen feed adjustment for target Mw/Mooney.

---

### 文件模块: `calibration_data_package.py`
**技术描述**: Calibration data package validation for V6.3.

**核心技术函数接口 (Functions)**:
- `load_calibration_data_package()`: Load or build a calibration data package without mutating defaults.
- `validate_calibration_dataset_units()`: Validate package-level and observation units.
- `calibration_data_lineage_dataframe()`: Return lineage rows for a calibration package.
- `calibration_package_dataframe()`: Return package observations as a report table.

---

### 文件模块: `calibration_loop.py`
**技术描述**: Closed-loop calibration, identifiability, uncertainty and DOE helpers.

**核心技术类 (Classes)**:
- `CalibrationLoopResult`: One closed-loop calibration and experimental-design summary.

**核心技术函数接口 (Functions)**:
- `rank_parameters_by_uncertainty()`: Rank parameters by weak identifiability and KPI uncertainty leverage.
- `recommend_experiments_for_weak_parameters()`: Return targeted experiments for weak parameter classes.
- `estimate_information_gain()`: Estimate relative information gain for candidate experiments.
- `run_calibration_loop()`: Run the lightweight calibration loop without triggering ODE/CFD/optimizer.

---

### 文件模块: `case_manager.py`
**技术描述**: Case and scenario management for the digital twin.

**核心技术类 (Classes)**:
- `CaseRecord`: Saved simulation case metadata and payload.

**核心技术函数接口 (Functions)**:
- `case_path()`: Return the JSON path for a case id.
- `save_case()`: Save a process case to a local JSON file.
- `load_case()`: Load a saved case record.
- `list_cases()`: List saved cases.
- `duplicate_case()`: Duplicate an existing saved case with a new name.
- `compare_cases()`: Compare two cases across input and KPI deltas.
- `case_record_from_json_bytes()`: Load a case from uploaded JSON bytes.
- `export_case_package()`: Export a reproducible case package as a zip archive.
- `import_case_package_zip()`: Import a case package zip and persist the contained case JSON.

---

### 文件模块: `components.py`
**技术描述**: Component data models and loaders.

**核心技术类 (Classes)**:
- `Component`: Pure component data used by simplified process calculations.

**核心技术函数接口 (Functions)**:
- `load_components()`: Load component records from data/components.json.
- `get_component()`: Return a component by name.
- `component_dataframe()`: Return component properties as a DataFrame for UI display.
- `solvent_names()`: Return available solvent identifiers.

---

### 文件模块: `conservation.py`
**技术描述**: Conservation and closure checks for process simulation results.

**核心技术类 (Classes)**:
- `ConservationResult`: One numerical conservation check.
- `ConservationDiagnostic`: Likely source and fix for a failed conservation check.

**核心技术函数接口 (Functions)**:
- `conservation_dataframe()`: Convert conservation results to a DataFrame.
- `conservation_diagnostics_dataframe()`: Convert conservation diagnostics to a DataFrame.
- `stream_mass()`: Return stream total mass flow in kg/h, handling missing streams.
- `total_mass_balance()`: Check overall process mass closure across feed, product and purge/recycle outputs.
- `component_mass_balance()`: Check a component or segment mass closure across the steady flowsheet.
- `reactor_monomer_polymer_balance()`: Check consumed monomer mass against polymer production.
- `segment_balance()`: Check E/P/D segment mass sum against polymer production.
- `flash_mass_balance()`: Check flash inlet mass equals vapor plus liquid outlet mass.
- `energy_release_balance()`: Check reaction heat equals consumed moles times heat of polymerization.
- `product_composition_balance()`: Check product C2/C3/ENB wt% sums to 100.
- `recycle_balance()`: Check recycle solver closure error is finite and within tolerance.
- `run_conservation_checks()`: Run the default conservation suite for a flowsheet result.
- `diagnose_conservation_results()`: Map failed conservation checks to likely model/stream sources.

---

### 文件模块: `constrained_window.py`
**技术描述**: Engineering-constrained process-window recommendation.

**核心技术类 (Classes)**:
- `WindowResult`: One robust process window candidate.

**核心技术函数接口 (Functions)**:
- `generate_feasible_windows()`: Generate feasible windows by perturbing the current fast flowsheet.
- `evaluate_window_robustness()`: Return a bounded robustness score.
- `rank_process_windows()`: Rank process windows by robustness and confidence.
- `recommend_validation_experiments_for_window()`: Return validation actions for one recommended process window.
- `constrained_windows_dataframe()`: Return process windows as a DataFrame.

---

### 文件模块: `data_assimilation.py`
**技术描述**: Evidence-aware data assimilation helpers for V6.3.

**核心技术函数接口 (Functions)**:
- `assimilate_benchmark_observations()`: Compare benchmark observations with model outputs using confidence weights.
- `update_calibrated_model_from_evidence()`: Create a calibrated property model from a validated data package.
- `data_assimilation_summary()`: Return bounded pass/fail summary for release gates.
- `data_assimilation_dataframe()`: Return assimilation rows plus source confidence.

---

### 文件模块: `data_lineage.py`
**技术描述**: Data-lineage records for benchmarks and calibration datasets.

**核心技术类 (Classes)**:
- `DataLineageRecord`: Provenance record for one benchmark or calibration dataset.

**核心技术函数接口 (Functions)**:
- `stable_data_hash()`: Return a stable short hash for data-lineage payloads.
- `lineage_confidence_from_record()`: Return a 0-100 lineage confidence score.
- `build_data_lineage_record()`: Build lineage metadata from one benchmark or dataset record.
- `lineage_for_benchmarks()`: Return lineage records for experimental/literature/synthetic benchmarks.
- `data_lineage_dataframe()`: Return benchmark/data lineage as a DataFrame.
- `lineage_confidence_score()`: Return average 0-100 lineage confidence score.
- `critical_benchmarks_missing_lineage()`: Return critical benchmark lineage failures for release gates.

---

### 文件模块: `data_lineage_graph.py`
**技术描述**: Data-lineage graph helpers for benchmarks and calibration datasets.

**核心技术函数接口 (Functions)**:
- `build_data_lineage_graph()`: Return benchmark -> source/data hash lineage edges.
- `data_lineage_graph_summary()`: Return compact data-lineage graph status.

---

### 文件模块: `db.py`
**技术描述**: Local SQLite data warehouse for reproducible EPDM digital-twin runs.

**核心技术函数接口 (Functions)**:
- `connect()`: Open a SQLite connection and initialize tables.
- `init_database()`: Create all V4 local data-warehouse tables.
- `insert_experiment()`: Insert or replace an experiment record.
- `import_experiments_dataframe()`: Import experiments from a DataFrame into SQLite.
- `query_experiments()`: Query experiments from SQLite as a normalized DataFrame.
- `save_model_run()`: Persist one model run with config hash and payload.
- `load_model_run()`: Load a stored model run payload by id.
- `list_model_runs()`: List model-run metadata.
- `save_json_record()`: Save a generic JSON record to parameter_sets, cases, reports or cfd_runs.

---

### 文件模块: `digital_twin_3d.py`
**技术描述**: High-level 3D digital twin views and equipment detail helpers.

**核心技术函数接口 (Functions)**:
- `available_view_modes()`: Return UI labels for digital-twin view modes.
- `selectable_equipment()`: Return equipment ids that can be highlighted in the 3D overview.
- `build_digital_twin_figure()`: Build the main 3D digital-twin overview figure.
- `equipment_detail_dataframe()`: Return a compact equipment table for the sidebar/detail panel.
- `figure_for_equipment()`: Return a focused 3D sketch for an equipment family.
- `equipment_detail_text()`: Return key values shown next to a selected 3D equipment item.

---

### 文件模块: `dimensional_checks.py`
**技术描述**: Simple dimensional and unit-conversion checks used by V4.6 reports.

**核心技术类 (Classes)**:
- `DimensionalCheckResult`: One unit/quantity consistency check.

**核心技术函数接口 (Functions)**:
- `kj_h_to_kw()`: Convert kJ/h to kW.
- `mol_L_to_mol_m3()`: Convert mol/L to mol/m3.
- `mpa_pa_consistency()`: Check MPa and Pa representations of pressure.
- `wt_fraction_consistency()`: Check wt% and fraction representations.
- `run_dimensional_checks()`: Run representative unit-conversion checks with optional sample overrides.
- `dimensional_checks_dataframe()`: Return dimensional checks as a DataFrame.

---

### 文件模块: `dimensioned.py`
**技术描述**: Lightweight dimensioned values for unit-safe scientific checks.

**核心技术类 (Classes)**:
- `DimensionedValue`: Numeric value carrying a unit, dimension and optional metadata.

**核心技术函数接口 (Functions)**:
- `dimension_for_unit()`: Return dimension for a supported unit.
- `assert_compatible_units()`: Raise if two units do not share a dimension.
- `convert_value()`: Convert a scalar value between compatible supported units.
- `as_dimensioned()`: Create a dimensioned value with metadata.
- `ensure_temperature_K()`: Return temperature in K and reject negative absolute temperature.
- `ensure_pressure_Pa()`: Return pressure in Pa and reject non-positive pressure.
- `ensure_mass_flow_kg_h()`: Return mass flow in kg/h and reject negative values.
- `ensure_molar_flow_mol_h()`: Return molar flow in mol/h and reject negative values.
- `ensure_concentration_mol_L()`: Return concentration in mol/L and reject negative values.
- `ensure_power_kW()`: Return power/heat duty in kW.
- `ensure_viscosity_Pa_s()`: Return viscosity in Pa.s and reject non-positive values.
- `ensure_density_kg_m3()`: Return density in kg/m3 and reject non-positive values.
- `ensure_length_m()`: Return length in m and reject non-positive values.
- `ensure_time_min()`: Return time/residence time in min and reject non-positive values.
- `mass_flow_to_molar_flow()`: Convert kg/h or g/h to mol/h using molecular weight.
- `molar_flow_to_mass_flow()`: Convert mol/h or kmol/h to kg/h using molecular weight.
- `unit_conversion_trace_dataframe()`: Return a unit-conversion trace used by reports and release gates.

---

### 文件模块: `doe_optimal.py`
**技术描述**: Feasible DOE recommendation helpers for parameter information gain.

**核心技术类 (Classes)**:
- `DOEOptimalResult`: Recommended next experiments.

**核心技术函数接口 (Functions)**:
- `recommend_optimal_doe()`: Return feasible DOE points covering kinetics, transfer and rheology parameters.

---

### 文件模块: `dynamic_reactor.py`
**技术描述**: Dynamic stirred-tank and semi-batch reactor model for EPDM solution polymerization.

**核心技术类 (Classes)**:
- `DynamicReactorConfig`: Configuration for realistic batch/semi-batch stirred-tank simulation.
- `DynamicReactorResult`: Time-profile output from the dynamic reactor model.

**核心技术函数接口 (Functions)**:
- `stage_timeline()`: Return a standard batch-polymerization operating timeline.
- `simulate_dynamic_reactor()`: Simulate a realistic stirred-tank, semi-batch, or transition polymerization cycle.
- `mixing_power()`: Estimate impeller Reynolds number, power and mixing regime.
- `dynamic_recommendations()`: Generate practical engineering recommendations from dynamic reactor traces.

---

### 文件模块: `dynamic_residuals.py`
**技术描述**: Dynamic ODE residual time-series checks for V5.4.

**核心技术类 (Classes)**:
- `DynamicResidualPoint`: One dynamic residual diagnostic row.

**核心技术函数接口 (Functions)**:
- `dynamic_residuals_dataframe()`: Calculate dynamic accumulation and reaction residuals from a profile.
- `dynamic_residual_system()`: Build a ResidualSystem from dynamic residual rows.
- `dynamic_residual_acceptance()`: Return dynamic residual acceptance summary.

---

### 文件模块: `dynamic_stability.py`
**技术描述**: Numerical stability checks for dynamic reactor profiles.

**核心技术类 (Classes)**:
- `DynamicStabilityResult`: One dynamic profile stability check.

**核心技术函数接口 (Functions)**:
- `dynamic_stability_dataframe()`: Return dynamic stability checks as a DataFrame.
- `check_dynamic_stability()`: Run non-negativity, boundedness and trend checks on an ODE profile.

---

### 文件模块: `dynamic_template_reactor.py`
**技术描述**: Template-driven semi-batch dynamic reactor approximation.

**核心技术类 (Classes)**:
- `DynamicTemplateResult`: Output from a template-driven dynamic reactor run.

**核心技术函数接口 (Functions)**:
- `simulate_template_semibatch_ode()`: Run a robust template-driven semi-batch reactor trajectory.

---

### 文件模块: `engineering_checks.py`
**技术描述**: Chemical-engineering sanity checks for simulation results.

**核心技术类 (Classes)**:
- `EngineeringCheckResult`: One engineering logic check result.

**核心技术函数接口 (Functions)**:
- `run_engineering_checks()`: Run mass, reactor, energy, transport and flash sanity checks.
- `checks_dataframe()`: Return engineering checks as a DataFrame.
- `overall_engineering_status()`: Return green/yellow/red status for a list of checks.

---

### 文件模块: `engineering_rules.py`
**技术描述**: Chemical-engineering trend rule registry and runner.

**核心技术类 (Classes)**:
- `EngineeringRule`: One expected engineering trend rule.
- `EngineeringRuleResult`: Result of one engineering trend check.

**核心技术函数接口 (Functions)**:
- `load_engineering_rules()`: Load engineering trend rules from JSON.
- `rules_dataframe()`: Return registered rules as a DataFrame.
- `rule_results_dataframe()`: Return rule results as a DataFrame.
- `run_engineering_rule()`: Run one registered engineering trend rule.
- `run_all_engineering_rules()`: Run all default trend rules. This is intended for explicit button use.

---

### 文件模块: `eos.py`
**技术描述**: Simplified cubic-EOS-inspired K-value helpers.

**核心技术函数接口 (Functions)**:
- `load_binary_interactions()`: Load binary interaction parameters for cubic EOS mixing rules.
- `binary_interaction()`: Return kij for a component pair, falling back to default when missing.
- `cubic_z_roots()`: Return real compressibility-factor roots for a pure-component cubic EOS.
- `fugacity_coefficient()`: Return pure-component fugacity coefficient for selected EOS phase root.
- `cubic_eos_details()`: Return PR/SRK pure-component EOS diagnostics: Z, phi and K.
- `cubic_eos_details()`: Return PR/SRK pure-component EOS diagnostics: Z, phi and K.
- `mixture_parameters()`: Calculate mixture 'a' and 'b' parameters using VdW one-fluid mixing rules.
- `mixture_ln_phi()`: Calculate mixture fugacity coefficients for each component.
- `cubic_eos_mixture_k_values()`: Calculate mixture K-values using fugacity coefficient ratios.
- `cubic_eos_k_value()`: Return a PR/SRK cubic-EOS K value with robust Wilson fallback.
- `eos_k_values()`: Return K values for component names using the simplified cubic EOS mode.
- `eos_details_table()`: Return EOS diagnostics rows for UI/reporting.
- `k_value_comparison()`: Compare Wilson, PR and SRK K values for components.

---

### 文件模块: `equation_binding.py`
**技术描述**: Bind equation registry records to implementation functions and trend checks.

**核心技术类 (Classes)**:
- `EquationBinding`: One registry-to-code binding.

**核心技术函数接口 (Functions)**:
- `import_implementation()`: Import an implementation function from a dotted path.
- `load_equation_bindings()`: Build bindings from equation registry plus V5.3 implementation metadata.
- `equation_binding_dataframe()`: Return equation bindings as a report table.
- `validate_equation_bindings()`: Return binding errors for critical equations.
- `run_equation_binding_checks()`: Run importability and metadata checks for release gates.
- `trend_smoke_results()`: Return lightweight finite trend checks for critical equations.

---

### 文件模块: `equation_registry.py`
**技术描述**: Machine-readable equation registry for formulas and model audit.

**核心技术类 (Classes)**:
- `EquationSpec`: One model equation and its unit metadata.

**核心技术函数接口 (Functions)**:
- `load_equation_registry()`: Load the equation registry from JSON.
- `equation_registry_dataframe()`: Return equations as a report table.
- `validate_equation_registry()`: Return schema-level warnings for incomplete equation records.
- `equations_by_module()`: Return equation ids grouped by module id.

---

### 文件模块: `equation_residual_coupling.py`
**技术描述**: Equation-residual-code coupling checks for V5.7.

**核心技术类 (Classes)**:
- `EquationResidualCoupling`: One equation-code-residual coupling record.

**核心技术函数接口 (Functions)**:
- `equation_residual_coupling_dataframe()`: Return critical equation to residual coupling records.
- `equation_residual_coupling_summary()`: Return compact release-gate summary for equation-residual coupling.
- `residual_sources_for_equations()`: Return equation_id -> residual_id mapping for diagnostics.

---

### 文件模块: `equation_reverse_check.py`
**技术描述**: Reverse checks from implementation output back to equation-registry rules.

**核心技术类 (Classes)**:
- `EquationReverseCheck`: One executable equation reverse-check row.

**核心技术函数接口 (Functions)**:
- `run_equation_reverse_checks()`: Return executable consistency checks for critical equation bindings.
- `equation_reverse_check_summary()`: Return compact release-gate summary.

---

### 文件模块: `equation_tests.py`
**技术描述**: Equation-registry to code consistency checks.

**核心技术类 (Classes)**:
- `EquationCodeCheck`: One formula-to-code behavioral check.

**核心技术函数接口 (Functions)**:
- `run_equation_code_checks()`: Run lightweight trend checks for critical registered equations.
- `equation_code_checks_dataframe()`: Return equation-code checks as a DataFrame.

---

### 文件模块: `equipment_3d.py`
**技术描述**: Plotly 3D equipment primitives and EPDM unit-operation sketches.

**核心技术类 (Classes)**:
- `EquipmentDescriptor`: Small equipment metadata block used by hover text and reports.

**核心技术函数接口 (Functions)**:
- `add_cylinder()`: Add a vertical cylinder shell to a 3D figure.
- `add_box()`: Add a cuboid-like marker for compact process units.
- `add_pipe()`: Add a colored material-transfer pipe/polyline.
- `add_label()`: Add a label at a process-equipment coordinate.
- `risk_color_from_kpis()`: Return a reactor shell color based on selected digital-twin layer.
- `reactor_3d_figure()`: Create a detailed stirred-tank reactor 3D sketch.
- `flash_vessel_3d_figure()`: Create a flash/devolatilizer 3D sketch.
- `product_tank_3d_figure()`: Create a polymer product tank sketch.
- `heat_exchanger_3d_figure()`: Create a preheater/cooling heat-exchanger sketch.
- `feed_area_3d_figure()`: Create a feed-preparation 3D sketch.
- `equipment_summary()`: Return an equipment summary table for UI and reports.

---

### 文件模块: `evidence_chain.py`
**技术描述**: Industrial evidence-chain governance for equation/residual/data lineage.

**核心技术函数接口 (Functions)**:
- `build_evidence_chain()`: Join traceability, source registry and data lineage into one audit chain.
- `evidence_gap_dataframe()`: Return missing evidence plus high-value experimental data gaps.
- `validate_evidence_chain_completeness()`: Return compact evidence-chain completeness status.
- `evidence_weighted_confidence()`: Return an evidence-weighted confidence score in [0, 100].
- `recommend_evidence_upgrade()`: Return concrete evidence-upgrade recommendations.

---

### 文件模块: `evidence_chain_score.py`
**技术描述**: Evidence-chain scoring helpers for V6.2 industrial confidence gates.

**核心技术函数接口 (Functions)**:
- `evidence_chain_score()`: Return a bounded score from completeness and source weights.
- `evidence_gap_priority_dataframe()`: Return prioritized evidence gaps including plant mass-balance reconciliation.
- `critical_evidence_chain_gate()`: Return release-gate status for critical evidence-chain completeness.
- `evidence_chain_score_dataframe()`: Return one-row evidence-chain score table.

---

### 文件模块: `experimental_benchmark.py`
**技术描述**: Experimental and standard-case benchmark metadata for V5.4.

**核心技术函数接口 (Functions)**:
- `load_experimental_benchmarks()`: Load experimental/literature/synthetic benchmark records.
- `benchmark_data_hash()`: Return a stable hash for one benchmark record excluding stored hash.
- `experimental_benchmarks_dataframe()`: Return experimental benchmark records with hash validation.
- `run_experimental_benchmark_checks()`: Run benchmark metadata acceptance checks without rerunning heavy models.
- `benchmark_confidence_score()`: Return 0-100 benchmark confidence score from source confidence levels.

---

### 文件模块: `experiment_data.py`
**技术描述**: Experiment data ingestion, normalization and quality checks.

**核心技术类 (Classes)**:
- `DataQualityReport`: Structured quality report for an experimental data table.

**核心技术函数接口 (Functions)**:
- `load_experiment_schema()`: Load the canonical experiment schema JSON.
- `load_experiment_file()`: Load a local CSV or Excel experiment table.
- `load_internal_experiment_dataset()`: Load and normalize the bundled internal experiment table.
- `normalize_experiments()`: Normalize incoming experimental data to the canonical schema.
- `quality_check_experiments()`: Check schema coverage, missing values, duplicates, bounds and robust outliers.
- `calibration_subset()`: Return rows with enough measured outputs for calibration.

---

### 文件模块: `feed_adapter.py`
**技术描述**: Template-aware feed stream construction and validation.

**核心技术类 (Classes)**:
- `FeedValidationResult`: One feed-map validation message.

**核心技术函数接口 (Functions)**:
- `validate_template_feed_map()`: Validate template monomer and chain-transfer feed maps before simulation.
- `build_template_feed_stream()`: Build a feed stream from a template feed map.

---

### 文件模块: `file_security.py`
**技术描述**: File-path safety and export metadata helpers.

**核心技术函数接口 (Functions)**:
- `validate_safe_filename()`: Return a safe filename or raise ValueError.
- `prevent_path_traversal()`: Resolve a path and ensure it stays under base_dir.
- `validate_upload_extension()`: Validate an upload extension against an allow-list.
- `validate_file_size()`: Validate a file size and return it.
- `export_metadata()`: Build metadata that every export can include without rerunning models.

---

### 文件模块: `flash.py`
**技术描述**: Flash unit operation using Rachford-Rice and Wilson K values.

**核心技术类 (Classes)**:
- `FlashResult`: Flash split result.
- `FlashDiagnostic`: Phase-split diagnostic for flash robustness and chemical logic.
- `Flash`: Isothermal flash unit operation.

**核心技术函数接口 (Functions)**:
- `diagnose_flash_result()`: Diagnose flash split bounds, fallback and component distribution.

---

### 文件模块: `flowsheet.py`
**技术描述**: Complete EPDM process flowsheet solver.

**核心技术函数接口 (Functions)**:
- `normalize_process_config()`: Normalize legacy/UI aliases into the canonical process configuration.
- `load_default_config()`: Load default process configuration from YAML.
- `build_process_graph()`: Return a directed graph for the default EPDM process topology.
- `build_feed_stream()`: Build the molecular feed stream from user process inputs.
- `calculate_preheat()`: Heat mixed feed to reactor temperature and return duty in kJ/h.
- `quench_reactor()`: Deactivate catalyst and account for a small quench addition.
- `run_flowsheet()`: Run the public EPDM flowsheet with robust error handling and template adapter support.

---

### 文件模块: `flowsheet_types.py`
**技术描述**: Data structures and types for the EPDM flowsheet solver.

**核心技术类 (Classes)**:
- `FlowsheetResult`: Full process simulation result.
- `ProcessConfig`: User-facing process configuration.

---

### 文件模块: `fluid_props.py`
**技术描述**: Mixture fluid properties, viscosity calibration and pipe hydraulics.

**核心技术类 (Classes)**:
- `ViscosityModelParameters`: Polymer solution viscosity model parameters.
- `RheologyModelParameters`: Optional non-Newtonian apparent-viscosity parameters.
- `FluidPropertyResult`: Calculated fluid property result for a process stream.
- `PipeHydraulicsResult`: Pipe pressure drop and pumping power result.

**核心技术函数接口 (Functions)**:
- `load_fluid_property_calibration()`: Load optional measured fluid property calibration data.
- `calibrate_viscosity_parameters()`: Fit A_mu, B_mu and alpha_Mw if measured calibration data exists.
- `mixture_molecular_weight()`: Calculate molecular mixture MW in g/mol from molecular mole fractions.
- `liquid_density()`: Calculate liquid mixture density by volume additivity.
- `mixture_cp()`: Calculate mass-weighted mixture heat capacity in kJ/kg/K.
- `gas_density()`: Calculate gas density by ideal gas equation in kg/m3.
- `solvent_log_mixed_viscosity()`: Calculate solvent/monomer viscosity by mole-fraction logarithmic mixing.
- `polymer_solution_viscosity()`: Calculate dynamic viscosity of polymer solution in Pa.s with numerical hardening.
- `apparent_viscosity()`: Return apparent viscosity for Newtonian, power-law or Carreau-Yasuda models.
- `thermal_conductivity()`: Calculate mass-weighted thermal conductivity in W/m/K.
- `mixture_vapor_pressure()`: Estimate mixture vapor pressure by mole-fraction weighted Wilson Psat.
- `fluid_fouling_risk()`: Estimate gel solution fouling/transport risk index.
- `calculate_fluid_properties()`: Calculate core mixture fluid properties for a stream.
- `estimate_stream_volumetric_flow_m3_h()`: Estimate volumetric flow rate from stream mass flow and density.
- `calculate_pipe_hydraulics()`: Calculate Darcy-Weisbach pressure drop and pump power.

---

### 文件模块: `governance_certificate.py`
**技术描述**: Model-governance certificate tables for V6.4 UI/report paths.

**核心技术函数接口 (Functions)**:
- `governance_certificate_dataframe()`: Return a compact governance certificate for UI and report use.
- `governance_certificate_summary()`: Return compact model-governance certificate status.
- `governance_certificate_gate()`: Return release-gate status for governance certificate data.

---

### 文件模块: `heat_balance.py`
**技术描述**: Reaction heat, cooling duty and heat-transfer calculations.

**核心技术类 (Classes)**:
- `HeatBalanceConfig`: Heat-balance inputs with engineering-estimate defaults.
- `HeatBalanceResult`: Calculated heat balance and heat-removal indicators.

**核心技术函数接口 (Functions)**:
- `calculate_reaction_heat()`: Return positive polymerization heat release in kJ/h.
- `thermal_risk_level()`: Classify adiabatic temperature-rise risk.
- `calculate_lmtd()`: Calculate jacket/cooler log-mean temperature difference in K.
- `heat_transfer_capacity_kW()`: Return maximum removable heat in kW and the LMTD in K.
- `calculate_heat_balance()`: Calculate reaction heat, adiabatic rise, cooling load and heat-transfer margin.

---

### 文件模块: `identifiability.py`
**技术描述**: Parameter identifiability diagnostics using finite-difference proxies.

**核心技术类 (Classes)**:
- `IdentifiabilityResult`: Fisher-information proxy and parameter identifiability summary.

**核心技术函数接口 (Functions)**:
- `finite_difference_sensitivity()`: Compute a finite-difference sensitivity matrix for key KPIs.
- `evaluate_identifiability()`: Evaluate parameter identifiability from sensitivity and data coverage.

---

### 文件模块: `industrial_data_package.py`
**技术描述**: Industrial calibration data package helpers for V6.4.

**核心技术函数接口 (Functions)**:
- `load_industrial_data_package()`: Load or normalize an industrial calibration data package.
- `validate_industrial_dataset_schema()`: Validate source, unit, uncertainty and validity metadata.
- `estimate_measurement_uncertainty()`: Return bounded uncertainty estimate for an industrial data package.
- `industrial_data_lineage_dataframe()`: Return data-lineage rows for an industrial package.
- `industrial_data_package_dataframe()`: Return package observations with validation metadata.

---

### 文件模块: `io_schema.py`
**技术描述**: Unified input/output schema metadata for core models.

**核心技术类 (Classes)**:
- `ModelInputSpec`: One model input field specification.
- `ModelOutputSpec`: One model output field specification.
- `ModelIOSchema`: Model IO schema used by registry, reports and UI diagnostics.

**核心技术函数接口 (Functions)**:
- `load_io_schemas()`: Return all built-in IO schemas.
- `get_io_schema()`: Return one IO schema by model id.
- `io_schema_dataframe()`: Return a flattened IO schema table.

---

### 文件模块: `kinetics.py`
**技术描述**: Polymerization kinetics for metallocene EPDM/EPM solution process.

**核心技术类 (Classes)**:
- `KineticParameters`: Apparent kinetic and chain-transfer parameters.
- `RateResult`: Apparent reaction rates and modifiers.

**核心技术函数接口 (Functions)**:
- `arrhenius()`: Return Arrhenius-adjusted apparent rate constant.
- `activation_factor()`: Return empirical active-center factor from Al/Ti and BHT ratios.
- `active_center_concentration()`: Estimate effective active center concentration in mol/L.
- `pressure_factor_enb()`: Return ENB insertion pressure penalty where pressure above 0.7 MPa is unfavorable.
- `ethylene_competition_factor()`: Return relative ENB insertion penalty from ethylene competition.
- `reaction_rates()`: Calculate apparent EPDM monomer insertion rates in mol/L/h.
- `calculate_template_rates()`: Calculate apparent monomer rates from a reaction template.
- `calculate_template_conversions()`: Return bounded fractional conversions for template monomers.
- `calculate_template_polymer_segments()`: Return polymer segment masses in kg/h from consumed mol/h.
- `estimate_molecular_weight()`: Estimate Mw from hydrogen chain transfer and composition modifiers.

---

### 文件模块: `kpi_adapter.py`
**技术描述**: Adapters from legacy flowsheet KPIs to template-aware KPI rows.

**核心技术函数接口 (Functions)**:
- `build_template_kpis()`: Build template-aware KPI rows while preserving EPDM compatibility aliases.
- `epdm_compatibility_kpis()`: Return EPDM-compatible KPI aliases from normalized KPI rows.

---

### 文件模块: `kpi_schema.py`
**技术描述**: Template-aware KPI schema and validation helpers.

**核心技术类 (Classes)**:
- `KPI`: One normalized KPI row.

**核心技术函数接口 (Functions)**:
- `validate_kpi_bounds()`: Return KPI rows with warnings populated for non-finite/out-of-range values.
- `kpis_to_dataframe()`: Convert KPI rows to a DataFrame.

---

### 文件模块: `layout_3d.py`
**技术描述**: 3D process-layout builder for the EPDM digital twin.

**核心技术函数接口 (Functions)**:
- `process_3d_layout()`: Build an interactive 3D process overview layout.

---

### 文件模块: `model_audit_report.py`
**技术描述**: Audit-grade model credibility report assembly.

**核心技术类 (Classes)**:
- `ModelAuditReport`: Traceable model audit report used by UI and report exports.

**核心技术函数接口 (Functions)**:
- `build_model_audit_report()`: Build a reproducible audit report from existing results only.

---

### 文件模块: `model_confidence.py`
**技术描述**: Model confidence scoring for R&D digital-twin outputs.

**核心技术类 (Classes)**:
- `ModelConfidenceCard`: A compact scorecard for model credibility and freshness.

**核心技术函数接口 (Functions)**:
- `build_model_confidence_card()`: Build a weighted model confidence card.

---

### 文件模块: `model_confidence_certificate.py`
**技术描述**: Model confidence certificate for V6.3 evidence governance.

**核心技术函数接口 (Functions)**:
- `generate_model_confidence_certificate()`: Generate a bounded, audit-ready model confidence certificate.
- `confidence_certificate_dataframe()`: Return one-row model confidence certificate table.
- `evidence_gap_priority_score()`: Return prioritized validation upgrade items.
- `validation_data_upgrade_plan()`: Return concrete validation upgrade plan rows.

---

### 文件模块: `model_confidence_engine.py`
**技术描述**: Evidence-weighted model confidence engine for V6.0.

**核心技术函数接口 (Functions)**:
- `model_confidence_score()`: Return evidence-weighted model confidence components.
- `confidence_decomposition()`: Return confidence components as a DataFrame.
- `recommend_high_value_validation_data()`: Return concrete high-value validation data gaps.
- `model_confidence_engine_dataframe()`: Return confidence decomposition plus data-gap summary rows.

---

### 文件模块: `model_contracts.py`
**技术描述**: Generic model contracts for simulation modules.

**核心技术类 (Classes)**:
- `ModelContract`: A normalized, implementation-independent model contract.

**核心技术函数接口 (Functions)**:
- `load_model_contracts()`: Load all active model contracts from the registry.
- `get_model_contract()`: Return one model contract by id.
- `contracts_dataframe()`: Return contracts as a UI/report table.

---

### 文件模块: `model_graph.py`
**技术描述**: Equation-residual-data model traceability graph for V6.0.

**核心技术函数接口 (Functions)**:
- `build_equation_graph()`: Return equation -> implementation/residual/benchmark traceability edges.
- `link_equation_to_residual()`: Return residual link metadata for one equation.
- `link_residual_to_benchmark()`: Return benchmark rows linked to a residual id.
- `link_benchmark_to_dataset()`: Return data-lineage link metadata for a benchmark id.
- `model_traceability_dataframe()`: Return one row per critical equation with equation/residual/data lineage.
- `model_traceability_summary()`: Return compact traceability gate status.

---

### 文件模块: `model_registry.py`
**技术描述**: Model registry for merged process-simulator and digital-twin capabilities.

**核心技术类 (Classes)**:
- `ModelModule`: A registered simulation, data, visualization or export module.

**核心技术函数接口 (Functions)**:
- `load_model_registry()`: Load registered model modules from ``data/model_registry.json``.
- `validate_model_registry()`: Return validation errors for registry entries.
- `module_trigger_dataframe()`: Return a UI-ready table of module trigger modes and applicability.
- `registry_summary()`: Summarize registry coverage for diagnostics and reports.

---

### 文件模块: `model_validation.py`
**技术描述**: Validation utilities for model contracts and registry entries.

**核心技术类 (Classes)**:
- `ModelValidationIssue`: One model-contract validation issue.

**核心技术函数接口 (Functions)**:
- `validate_model_contract()`: Validate one model contract for completeness and UI safety.
- `validate_all_model_contracts()`: Validate registry and all active model contracts.
- `validation_dataframe()`: Return all model-validation issues as a DataFrame.

---

### 文件模块: `numerics.py`
**技术描述**: Numerical stability helpers shared by model governance layers.

**核心技术函数接口 (Functions)**:
- `finite_or_default()`: Return a finite float or a default value.
- `nonnegative()`: Return a finite non-negative float.
- `bounded()`: Return a finite value clipped to [low, high].
- `normalize_to_sum()`: Normalize a mapping or sequence to a target sum.
- `safe_exp()`: Return exp(x) with bounded exponent.
- `safe_log()`: Return log(max(x, floor)) with finite protection.
- `safe_power()`: Return a finite power result or default.
- `finite_dict()`: Replace non-finite numeric values inside a flat mapping.
- `validate_kpi_finiteness()`: Return KPI keys with non-finite numeric values.

---

### 文件模块: `ode_diagnostics.py`
**技术描述**: Diagnostics for template ODE profiles and solver summaries.

**核心技术类 (Classes)**:
- `ODEDiagnostic`: One ODE diagnostic row.
- `RHSTermDiagnostic`: One physically named RHS contribution diagnostic.

**核心技术函数接口 (Functions)**:
- `diagnose_dynamic_ode()`: Diagnose numerical and physical consistency of a dynamic ODE result.
- `ode_diagnostics_dataframe()`: Return ODE diagnostics as a DataFrame.
- `rhs_term_schema_dataframe()`: Document RHS terms and units for audit reports.
- `rhs_terms_diagnostics_dataframe()`: Return RHS term diagnostics with units and physical meaning.

---

### 文件模块: `ode_events.py`
**技术描述**: Reusable ODE event helpers for template dynamic reactors.

**核心技术类 (Classes)**:
- `ODEEventRecord`: One dynamic-reactor event entry.

**核心技术函数接口 (Functions)**:
- `quench_event()`: Event function crossing zero at quench time.
- `runaway_event()`: Event function crossing zero at high-temperature alarm.
- `feed_cutoff_event()`: Event function crossing zero when pressure reaches the feed cutoff.
- `end_reaction_event()`: Event function crossing zero at recipe end.
- `event_log_dataframe()`: Return event records as a DataFrame.

---

### 文件模块: `ode_jacobian.py`
**技术描述**: Finite-difference Jacobian helpers for template ODE stiff solvers.

**核心技术类 (Classes)**:
- `JacobianDiagnostic`: Small diagnostic summary for a finite-difference Jacobian.

**核心技术函数接口 (Functions)**:
- `finite_difference_jacobian()`: Return a central finite-difference Jacobian for dy/dt=f(t,y).
- `scaled_finite_difference_jacobian()`: Return Jacobian for a scaled state vector y_scaled=y/scales.
- `jacobian_diagnostic()`: Return finite/size diagnostics without expensive exact conditioning.

---

### 文件模块: `ode_scaling.py`
**技术描述**: State scaling helpers and BDF readiness diagnostics for template ODEs.

**核心技术类 (Classes)**:
- `BDFReadiness`: BDF readiness diagnostic.

**核心技术函数接口 (Functions)**:
- `scale_state_vector()`: Scale an ODE state vector by positive characteristic scales.
- `unscale_state_vector()`: Reverse scale_state_vector.
- `estimate_state_scales()`: Estimate positive characteristic scales for a template state layout.
- `bdf_readiness_check()`: Return whether the current MVP should attempt BDF or fallback.

---

### 文件模块: `optimizer.py`
**技术描述**: Process optimizer for target EPDM/EPM grades.

**核心技术类 (Classes)**:
- `OptimizationResult`: Optimization output for Streamlit and reports.

**核心技术函数接口 (Functions)**:
- `optimize_for_grade()`: Optimize operating window for a target grade using differential evolution.

---

### 文件模块: `parameter_constraints.py`
**技术描述**: Physical parameter constraints for estimation, posterior and uncertainty.

**核心技术类 (Classes)**:
- `ParameterConstraintResult`: One parameter-constraint validation result.

**核心技术函数接口 (Functions)**:
- `parameter_constraints_dataframe()`: Return configured parameter constraints.
- `validate_parameter_value()`: Validate one parameter against physical bounds.
- `validate_parameter_set()`: Validate a parameter dictionary.
- `parameter_constraint_results_dataframe()`: Return parameter validation results as a DataFrame.

---

### 文件模块: `parameter_estimation.py`
**技术描述**: Nonlinear parameter estimation and parameter-set version management.

**核心技术类 (Classes)**:
- `ParameterEstimationResult`: Output from nonlinear parameter estimation.

**核心技术函数接口 (Functions)**:
- `default_estimation_parameters()`: Return the default estimation parameter dictionary.
- `load_parameter_sets()`: Load parameter-set registry.
- `parameter_sets_dataframe()`: Return parameter sets as a compact table.
- `save_parameter_set()`: Save a parameter set without overwriting built-in defaults unless explicitly requested.
- `set_active_parameter_set()`: Set the active parameter set in the registry.
- `get_parameter_set_parameters()`: Return a full parameter dictionary for a set id, falling back to defaults.
- `kinetic_parameters_from_set()`: Build KineticParameters from a stored parameter set.
- `estimate_parameters()`: Estimate apparent model parameters from normalized experimental data.

---

### 文件模块: `pareto.py`
**技术描述**: Multi-objective process-window scan and Pareto frontier selection.

**核心技术类 (Classes)**:
- `ParetoResult`: Pareto scan result.

**核心技术函数接口 (Functions)**:
- `generate_pareto_windows()`: Generate feasible candidates and a simple nondominated frontier.

---

### 文件模块: `phase_equilibrium_constraints.py`
**技术描述**: Phase-equilibrium physical constraints and flash residual diagnostics.

**核心技术类 (Classes)**:
- `PhaseEquilibriumConstraint`: One physical constraint check for K-values, EOS roots or flash split.

**核心技术函数接口 (Functions)**:
- `classify_z_roots()`: Classify cubic-EOS roots and fugacity diagnostics for one component.
- `k_value_ordering_dataframe()`: Return K-value ordering checks for light/heavy/polymer pseudo components.
- `flash_residuals_dataframe()`: Return RR, phase, polymer-vapor and total-mass residual rows for a flash result.
- `phase_equilibrium_constraints_dataframe()`: Return default phase-equilibrium physical constraint checks.

---

### 文件模块: `plotting.py`
**技术描述**: Plotly visualization helpers.

**核心技术函数接口 (Functions)**:
- `flowsheet_block_diagram()`: Return a simple block flowsheet diagram.
- `sankey_material()`: Return a Sankey diagram for major material flows.
- `conversion_bar()`: Return monomer conversion bar chart.
- `composition_bar()`: Return product composition stacked bar.
- `flash_split_chart()`: Return vapor/liquid split chart.
- `sensitivity_line()`: Return line plot for one-dimensional sensitivity results.
- `sensitivity_heatmap()`: Return heatmap for two-dimensional sensitivity results.
- `optimization_convergence()`: Return optimization convergence plot.
- `property_curve()`: Return a generic property curve plot.

---

### 文件模块: `plot_validation.py`
**技术描述**: Plotly figure validation for scientific visualization release gates.

**核心技术类 (Classes)**:
- `PlotValidationResult`: One figure validation result.

**核心技术函数接口 (Functions)**:
- `validate_nonempty_figure()`: Validate a figure has renderable traces.
- `validate_axis_labels()`: Validate axis labels for 2D numeric plots.
- `validate_colorbar_labels()`: Validate contour/surface-like traces expose a colorbar or hover units.
- `validate_plotly_figure_units()`: Run nonempty, axis and colorbar validations for one figure.
- `plot_validation_dataframe()`: Return validation results for a mapping of named Plotly figures.

---

### 文件模块: `polymer_props.py`
**技术描述**: Empirical polymer property models and grade matching.

**核心技术函数接口 (Functions)**:
- `predict_polymer_properties()`: Dispatch polymer property predictions through the V4.5 template layer.
- `load_internal_experiments()`: Load internal experiment data used for calibration.
- `load_target_grades()`: Load target grade definitions.
- `grade_target_value()`: Return a single target value for a grade metric.
- `grade_bounds()`: Return min/max grade bounds, deriving them from target when needed.
- `calibrate_mooney_coefficients()`: Fit Mooney model coefficients from internal experiments.
- `calibrate_enb_feed_relationship()`: Fit a simple ENB feed-to-product empirical relationship.
- `estimate_mooney()`: Estimate Mooney viscosity ML(1+4) from empirical logarithmic model.
- `estimate_tg()`: Estimate glass transition temperature by a Fox equation in Celsius.
- `estimate_tm_and_crystallinity()`: Estimate melting peak and crystallization risk from ethylene content.
- `fouling_risk_index()`: Estimate normalized fouling and transfer risk.
- `grade_match()`: Score current product against a target grade definition.
- `generate_recommendations()`: Generate engineering recommendations from simulation KPIs.

---

### 文件模块: `posterior.py`
**技术描述**: Lightweight posterior sampling for R&D parameter uncertainty.

**核心技术类 (Classes)**:
- `PosteriorResult`: Result from lightweight MCMC sampling.

**核心技术函数接口 (Functions)**:
- `log_prior_bounds()`: Return a simple uniform log prior inside bounds, -inf outside.
- `log_likelihood_proxy()`: Return a stable proxy likelihood against endpoint experiment data.
- `posterior_summary()`: Return summary, credible intervals and correlation tables.
- `run_lightweight_mcmc()`: Run a bounded random-walk Metropolis sampler.
- `posterior_to_uncertainty_inputs()`: Convert posterior intervals to uncertainty percentages.

---

### 文件模块: `posterior_residual_filter.py`
**技术描述**: Residual acceptance filters for posterior and uncertainty samples.

**核心技术函数接口 (Functions)**:
- `residual_penalty_for_sample()`: Return residual plus parameter-bound penalty for one posterior sample.
- `filter_posterior_samples_by_residual()`: Annotate posterior samples with residual and parameter acceptance.
- `residual_acceptance_rate()`: Return posterior residual acceptance rate in [0, 1].
- `posterior_residual_filter_dataframe()`: Return report-safe posterior residual filter output.

---

### 文件模块: `preflight.py`
**技术描述**: Pre-run dimensional and physical input validation.

**核心技术类 (Classes)**:
- `PreflightResult`: One pre-run validation item.

**核心技术函数接口 (Functions)**:
- `preflight_dataframe()`: Return preflight results as a DataFrame.
- `has_blocking_failures()`: Return True when any preflight result blocks execution.
- `run_preflight_for_model()`: Validate a model input payload against IO schema numeric bounds.
- `run_preflight_for_flowsheet()`: Validate flowsheet inputs before running the fast model.
- `run_preflight_for_cfd()`: Validate CFD inputs.
- `run_preflight_for_optimizer()`: Validate optimization bounds and target grade.

---

### 文件模块: `profile_alignment.py`
**技术描述**: Model-experiment dynamic profile alignment and residual metrics.

**核心技术函数接口 (Functions)**:
- `align_model_to_experiment()`: Interpolate model columns onto experimental time points without mutating inputs.
- `calculate_profile_residuals()`: Calculate model-minus-experiment residuals for aligned profile columns.
- `profile_fit_score()`: Return RMSE/MAE for each residual column.

---

### 文件模块: `property_calibration.py`
**技术描述**: R&D property calibration utilities for viscosity and heat-release inputs.

**核心技术类 (Classes)**:
- `PropertyCalibrationResult`: Calibration result with finite diagnostics and audit metadata.

**核心技术函数接口 (Functions)**:
- `calibration_metrics()`: Return MAE/RMSE/R2 metrics for calibration residuals.
- `save_property_calibration_result()`: Persist a calibrated property set without modifying defaults.
- `property_calibration_score()`: Return a bounded completeness/quality score for property calibration.
- `calibrate_viscosity_model()`: Fit EPDM apparent viscosity parameters from rheology observations.
- `calibrate_heat_release()`: Fit an apparent heat of polymerization from calorimetry data.

---

### 文件模块: `property_confidence.py`
**技术描述**: Property source and confidence metadata.

**核心技术类 (Classes)**:
- `PropertySource`: One property value and provenance record.

**核心技术函数接口 (Functions)**:
- `load_property_sources()`: Load property source metadata.
- `property_confidence_dataframe()`: Return property sources as a DataFrame.
- `get_property_confidence()`: Return confidence metadata for one component property.
- `propagate_property_uncertainty_to_model_confidence()`: Aggregate property-confidence metadata into a model-confidence contribution.

---

### 文件模块: `property_models.py`
**技术描述**: Template-dispatched polymer property models.

**核心技术类 (Classes)**:
- `PolymerPropertyResult`: Template-dispatched polymer property result.

**核心技术函数接口 (Functions)**:
- `predict_polymer_properties()`: Dispatch polymer property prediction by reaction-template property model.
- `property_models_dataframe()`: Return available template property models as a table.

---

### 文件模块: `property_model_bridge.py`
**技术描述**: Bridge calibrated property-model selection into calculation paths.

**核心技术函数接口 (Functions)**:
- `bridge_property_value()`: Return a property value with explicit default/calibrated provenance.
- `property_model_bridge_dataframe()`: Return V6.1 bridge rows for Henry, viscosity, flash-K and deltaH.
- `property_bridge_confidence_adjustment()`: Return confidence adjustment from selected property-model bridge rows.

---

### 文件模块: `property_model_runtime.py`
**技术描述**: Runtime application of calibrated property models for V6.2.

**核心技术函数接口 (Functions)**:
- `runtime_henry_cstar()`: Return Henry Cstar with optional calibrated model applied.
- `runtime_rheology_viscosity()`: Return rheology viscosity with optional calibrated model applied.
- `runtime_flash_k_values()`: Return flash K values with an optional calibrated correction factor.
- `runtime_heat_release()`: Return heat release with optional calibrated deltaH magnitude.
- `property_model_runtime_dataframe()`: Return V6.2 runtime property-model application rows.

---

### 文件模块: `property_model_selector.py`
**技术描述**: Calibrated property model selector for V6.0 flowsheet governance.

**核心技术函数接口 (Functions)**:
- `property_model_selector()`: Select a property model and report confidence/validity diagnostics.
- `apply_selected_property_model()`: Apply selected calibrated property parameter to a base value.
- `property_model_selection_dataframe()`: Return property selector rows for Henry, viscosity, flash-K and deltaH.

---

### 文件模块: `property_runtime_audit.py`
**技术描述**: Audit calibrated property-model runtime effects for V6.4.

**核心技术函数接口 (Functions)**:
- `property_runtime_audit_dataframe()`: Return runtime property audit rows with residual acceptance status.
- `property_runtime_audit_summary()`: Return compact property runtime audit status.
- `property_runtime_audit_gate()`: Return release-gate status for property runtime audit.

---

### 文件模块: `property_runtime_context.py`
**技术描述**: Property runtime context for V6.3 calibrated-model execution.

**核心技术函数接口 (Functions)**:
- `build_property_runtime_context()`: Build property runtime context and residual-safety status.
- `property_runtime_context_dataframe()`: Return property runtime context rows joined with runtime property values.
- `property_runtime_context_summary()`: Return compact gate status for property runtime context.

---

### 文件模块: `reaction_templates.py`
**技术描述**: Reaction template metadata for extensible polymerization models.

**核心技术类 (Classes)**:
- `ReactionTemplate`: A reusable apparent polymerization reaction template.

**核心技术函数接口 (Functions)**:
- `load_reaction_templates()`: Load reaction templates from local JSON.
- `get_reaction_template()`: Return one reaction template by id.
- `default_epdm_template()`: Return the default EPDM/EPM metallocene solution template.
- `segment_map_from_template()`: Return monomer-to-polymer-segment mapping.
- `monomers_from_template()`: Return monomer names from a reaction template.
- `molecular_weights_from_template()`: Return monomer molecular weights in g/mol from a reaction template.
- `template_with_fallback()`: Return a template and warnings, falling back to the default EPDM template.
- `heat_balance_deltaH_from_template()`: Return default polymerization heats in kJ/mol.
- `property_model_from_template()`: Return a normalized property-model dispatch dictionary.
- `templates_dataframe()`: Return reaction templates as a report table.

---

### 文件模块: `reactor.py`
**技术描述**: Polymerization reactor models.

**核心技术类 (Classes)**:
- `ReactorStage`: One reactor stage result.
- `ReactorResult`: Aggregated reactor calculation result.
- `DynamicSemibatchODEResult`: Detailed semi-batch ODE simulation result.

**核心技术函数接口 (Functions)**:
- `estimate_liquid_volume_flow_L_h()`: Estimate liquid volume flow from mass flows and component densities.
- `simulate_reactor()`: Simulate batch, single CSTR, CSTR-series, or plug-flow-approximation EPDM polymerization.
- `simulate_dynamic_semibatch_ode()`: Simulate a pressure-fed semi-batch stirred-tank polymerization with solve_ivp.

---

### 文件模块: `recipe.py`
**技术描述**: Recipe engine for dynamic semi-batch EPDM polymerization.

**核心技术类 (Classes)**:
- `RecipeStep`: One time-bounded operating step in a semi-batch recipe.
- `Recipe`: Serializable recipe composed of ordered RecipeStep records.

**核心技术函数接口 (Functions)**:
- `default_semibatch_recipe()`: Return a default staged recipe consistent with the UI polymerization timeline.
- `recipe_from_dict()`: Build a Recipe from JSON-like dict data.
- `recipe_from_json()`: Load a recipe from JSON text.
- `recipe_to_dataframe()`: Return recipe steps as a UI-editable DataFrame.
- `recipe_from_dataframe()`: Build a Recipe from an edited DataFrame.
- `recipe_event_log()`: Return all recipe events as a chronological table.
- `recipe_to_ode_config()`: Map a recipe to the existing ODE config dictionary.

---

### 文件模块: `recycle_solver.py`
**技术描述**: Iterative recycle tear-stream solver for simplified EPDM flowsheets.

**核心技术类 (Classes)**:
- `RecycleSolverResult`: Result from a fixed-point recycle calculation.

**核心技术函数接口 (Functions)**:
- `solve_recycle()`: Solve recycle loops using Wegstein-accelerated fixed-point iteration.

---

### 文件模块: `report_consistency.py`
**技术描述**: Report/repro-package metadata consistency checks.

**核心技术类 (Classes)**:
- `ReportConsistencyResult`: One report consistency gate result.

**核心技术函数接口 (Functions)**:
- `excel_sheet_names()`: Return workbook sheet names without writing to disk.
- `check_excel_required_sheets()`: Check required report sheets are present.
- `read_excel_metadata()`: Read the first row of the export_metadata sheet.
- `load_repro_manifest()`: Load manifest.json from a repro package zip.
- `compare_report_manifest_metadata()`: Compare stable metadata keys between report and repro manifest.
- `check_export_does_not_run_heavy()`: Check report export metadata does not indicate hidden heavy-task execution.
- `report_consistency_dataframe()`: Return all report consistency checks as a table.

---

### 文件模块: `repro_package.py`
**技术描述**: Audit-grade reproducibility package export/import.

**核心技术类 (Classes)**:
- `ReproPackageManifest`: Manifest for a reproducible case package.

**核心技术函数接口 (Functions)**:
- `build_repro_manifest()`: Build a reproducibility manifest from existing results only.
- `export_repro_package()`: Export a zip package with enough metadata to reproduce the case.
- `load_repro_manifest_from_zip()`: Load manifest.json from a reproducibility package.

---

### 文件模块: `residual_acceptance.py`
**技术描述**: Residual acceptance policies for calibration, DOE, optimizer and posterior.

**核心技术函数接口 (Functions)**:
- `residual_acceptance_record()`: Return a uniform residual-acceptance record.
- `residual_acceptance_dataframe()`: Return residual acceptance rows for multiple model consumers.
- `calibrated_set_residual_acceptance()`: Return whether a calibrated parameter/property set may be saved.
- `optimizer_residual_acceptance()`: Return optimizer residual acceptance and penalty.
- `doe_residual_acceptance()`: Return DOE residual acceptance for a candidate/result payload.

---

### 文件模块: `residual_aware_decision.py`
**技术描述**: Residual-aware posterior, uncertainty and DOE decision helpers.

**核心技术函数接口 (Functions)**:
- `reject_residual_critical_candidate()`: Return rejection status for a residual critical candidate.
- `residual_risk_score()`: Return a bounded residual risk score in [0, 1].
- `residual_aware_doe_score()`: Score a DOE candidate from residual risk, validity edge and lineage confidence.
- `residual_aware_posterior_weight()`: Return posterior sample weight after residual and parameter penalties.
- `residual_aware_uncertainty_risk()`: Combine base risk probability with residual risk while keeping [0, 1].
- `residual_aware_decision_dataframe()`: Return a report-safe audit table for residual-aware decisions.

---

### 文件模块: `residual_aware_decision_engine.py`
**技术描述**: Unified residual-aware decision engine for V6.4.

**核心技术函数接口 (Functions)**:
- `residual_aware_decision_engine()`: Return one residual-aware optimizer/DOE/posterior decision.
- `residual_decision_engine_dataframe()`: Return decision-engine audit rows.
- `residual_decision_engine_gate()`: Return release-gate status for the residual-aware decision engine.

---

### 文件模块: `residual_aware_doe.py`
**技术描述**: Residual-aware DOE candidate scoring for V6.2.

**核心技术函数接口 (Functions)**:
- `residual_aware_doe_candidate_score()`: Score DOE candidate with residual, validity, lineage and benchmark signals.
- `filter_residual_aware_doe_candidates()`: Return scored DOE candidates, excluding residual-critical or outside-validity recommendations.
- `residual_aware_doe_dataframe()`: Return default DOE decision audit rows.

---

### 文件模块: `residual_aware_optimizer.py`
**技术描述**: Residual-aware optimizer objective helpers for V6.2.

**核心技术函数接口 (Functions)**:
- `residual_aware_optimizer_objective()`: Return process objective plus residual and validity penalties.
- `reject_optimizer_candidate()`: Reject optimizer candidates outside validity or with critical residuals.
- `residual_aware_optimizer_dataframe()`: Return optimizer decision audit rows.

---

### 文件模块: `residual_aware_sampling.py`
**技术描述**: Residual-aware sampling decisions for V6.3 posterior/DOE/optimizer paths.

**核心技术函数接口 (Functions)**:
- `residual_aware_sample_weight()`: Return bounded sample weight after residual and uncertainty penalties.
- `residual_aware_sampling_decision()`: Return one residual-aware sampling decision.
- `residual_aware_sampling_dataframe()`: Return residual-aware sampling audit table.

---

### 文件模块: `residual_graph.py`
**技术描述**: Residual graph and suspected-source traceability for V6.0.

**核心技术函数接口 (Functions)**:
- `build_residual_graph()`: Return residual -> suspected source/fix graph rows.
- `residual_traceability_summary()`: Return compact residual graph status.

---

### 文件模块: `residual_objective.py`
**技术描述**: Residual-driven objective and filtering helpers for V5.4 gates.

**核心技术函数接口 (Functions)**:
- `residual_objective_score()`: Return a nonnegative optimizer penalty from residual-system quality.
- `reject_if_critical_residual()`: Return a compact critical-residual acceptance record.
- `residual_penalty_for_optimizer()`: Return a weighted residual penalty suitable for optimizer objectives.
- `residual_filter_for_doe()`: Return DOE feasibility status using an attached ResidualSystem/result.
- `residual_diagnostics_dataframe()`: Return detailed residual diagnostics with objective columns.

---

### 文件模块: `residual_solver.py`
**技术描述**: Residual-driven closure helpers for V5.5.

**核心技术类 (Classes)**:
- `ResidualCorrection`: One bounded residual correction proposal.

**核心技术函数接口 (Functions)**:
- `residual_weighted_objective()`: Return a residual objective that strongly penalizes critical failures.
- `solve_recycle_with_residual_minimization()`: Return a bounded recycle tear correction proposal.
- `adjust_flash_split_to_close_mass()`: Return a small flash liquid correction to close total mass.
- `heat_balance_residual_correction()`: Return a bounded heat-balance reporting correction.
- `residual_acceptance_summary()`: Return an audit-ready residual acceptance summary.
- `residual_correction_trace_dataframe()`: Return correction proposals as a report table.
- `residual_solver_dataframe()`: Return a compact residual-solver gate table.

---

### 文件模块: `residual_system.py`
**技术描述**: Conservation residual system used by V5.3 math-core gates.

**核心技术类 (Classes)**:
- `Residual`: One conservation or numerical residual.
- `ResidualSystem`: Grouped residuals for flowsheet, dynamic ODE and report gates.

**核心技术函数接口 (Functions)**:
- `make_residual()`: Create a finite residual with relative error and severity.
- `score_residuals()`: Return a 0-100 residual-system score.
- `critical_residuals()`: Return residuals that should block release, DOE or optimizer recommendations.
- `residual_system_acceptance()`: Return a compact acceptance record for gates, DOE and optimizer filters.
- `build_flowsheet_residual_system()`: Build mass, phase, reaction and heat residuals for a flowsheet result.
- `build_dynamic_residual_system()`: Build simple dynamic accumulation residuals for a template ODE profile.
- `residual_system_dataframe()`: Return residual system as a DataFrame.

---

### 文件模块: `rheology.py`
**技术描述**: Unified Newtonian and non-Newtonian rheology models.

**核心技术类 (Classes)**:
- `RheologyParameters`: Rheology parameter set for polymer solution apparent viscosity.
- `RheologyResult`: Rheology calculation output.

**核心技术函数接口 (Functions)**:
- `zero_shear_solution_viscosity()`: Return finite positive zero-shear solution viscosity in Pa.s.
- `apparent_viscosity_from_zero_shear()`: Return apparent viscosity for Newtonian, power-law or Carreau-Yasuda models.
- `calculate_rheology()`: Calculate dynamic and apparent viscosity with trend-safe guards.
- `rheology_models_dataframe()`: Return supported rheology model names.

---

### 文件模块: `safety.py`
**技术描述**: Thermal safety screening for R&D EPDM polymerization cases.

**核心技术类 (Classes)**:
- `SafetyResult`: Thermal safety and runaway screening result.

**核心技术函数接口 (Functions)**:
- `calculate_safety()`: Calculate a compact heat-safety screen from flowsheet and optional time-series data.

---

### 文件模块: `scaleup.py`
**技术描述**: Kettle scale-up and engineering similarity calculations.

**核心技术类 (Classes)**:
- `ScaleUpCase`: Single stirred-kettle scale-up case.
- `ScaleUpResult`: Scale-up metrics for one reactor scale.

**核心技术函数接口 (Functions)**:
- `power_number()`: Estimate impeller power number from type and Reynolds regime.
- `default_tank_diameter()`: Estimate a lab-kettle tank diameter from volume assuming H/T about 1.2.
- `calculate_scaleup_case()`: Calculate stirred-kettle engineering-similarity metrics.
- `compare_scaleup()`: Compare 2 L, 5 L and a custom kettle scale against the 2 L reference.

---

### 文件模块: `scientific_benchmarks.py`
**技术描述**: Golden scientific benchmark runner for release-gate regression checks.

**核心技术类 (Classes)**:
- `BenchmarkCheck`: One benchmark result.

**核心技术函数接口 (Functions)**:
- `benchmark_definitions()`: Load benchmark metadata.
- `run_scientific_benchmarks()`: Run stable scientific benchmark checks.
- `unit_roundtrip_checks()`: Return deterministic unit roundtrip checks used by property tests.

---

### 文件模块: `sensitivity.py`
**技术描述**: Sensitivity analysis helpers.

**核心技术函数接口 (Functions)**:
- `scan_single_variable()`: Run a one-dimensional sensitivity scan.
- `scan_two_variables()`: Run a two-dimensional sensitivity scan.
- `default_values_for_variable()`: Return sensible default scan values for a variable.

---

### 文件模块: `solubility.py`
**技术描述**: Henry-law style gas solubility correlations for EPDM solution polymerization.

**核心技术类 (Classes)**:
- `SolubilityRecord`: Reference solubility model parameters.

**核心技术函数接口 (Functions)**:
- `load_solubility_records()`: Return gas solubility records loaded from data/solubility_parameters.json.
- `solubility_records_dataframe()`: Return the built-in gas solubility records.
- `calibrate_henry_parameters()`: Fit a single Henry reference coefficient from measured Cstar data.
- `liquid_saturation_concentration_mol_L()`: Return saturated liquid concentration in mol/L with high-pressure Poynting correction.
- `gas_liquid_saturation_table()`: Return saturation concentrations for C2/C3/H2 gas mixture.
- `gas_mole_fractions_from_feeds()`: Build gas mole fractions from arbitrary positive mole-like feed values.
- `henry_cstar_comparison()`: Return a table comparing base and catalyst-corrected Henry Cstar values.

---

### 文件模块: `state.py`
**技术描述**: Application state models for cached, modular simulation workflows.

**核心技术类 (Classes)**:
- `SimulationState`: Single source of truth for user-facing simulation controls.
- `ResultsStore`: Lightweight in-session result cache for UI pages.

---

### 文件模块: `state_vector.py`
**技术描述**: Template-driven dynamic reactor state-vector utilities.

**核心技术类 (Classes)**:
- `StateVectorLayout`: Ordered state-vector layout generated from a reaction template.

**核心技术函数接口 (Functions)**:
- `build_state_layout_from_template()`: Build an ordered dynamic state layout from a reaction template.
- `default_state_dict()`: Return a nested zero state with physically meaningful defaults.
- `pack_state()`: Pack a nested state dictionary into a flat numpy vector.
- `unpack_state()`: Unpack a flat vector into a nested state dictionary.
- `validate_state_nonnegative()`: Return warnings for negative or non-finite state entries.
- `clamp_state_nonnegative()`: Return a copy with extensive variables clipped to non-negative values.

---

### 文件模块: `streams.py`
**技术描述**: Material stream data structures.

**核心技术类 (Classes)**:
- `Stream`: Process stream with component molar and mass flow rates.

**核心技术函数接口 (Functions)**:
- `mix_streams()`: Mix streams by adding molar, mass, polymer and segment flows.

---

### 文件模块: `surrogate.py`
**技术描述**: Physical-constraint surrogate models for fast process screening.

**核心技术类 (Classes)**:
- `SurrogateModel`: Small local surrogate with explicit validity and physics metadata.

**核心技术函数接口 (Functions)**:
- `train_surrogate_from_sensitivity_results()`: Train a finite linear/ridge surrogate from sensitivity results.
- `predict_with_surrogate()`: Predict finite outputs with applicability warning handled separately.
- `surrogate_applicability_warning()`: Return warnings for out-of-training-range inputs.
- `validate_surrogate_physics()`: Check encoded monotonic physical constraints against coefficient signs.

---

### 文件模块: `template_config.py`
**技术描述**: Template-aware process configuration adapters.

**核心技术类 (Classes)**:
- `TemplateProcessConfig`: Template-driven process configuration with EPDM compatibility fields.

**核心技术函数接口 (Functions)**:
- `process_config_to_template_config()`: Convert a legacy config to the template-aware representation.
- `template_config_to_process_config()`: Convert a template config back to the EPDM-compatible process config.
- `epdm_feed_aliases()`: Return legacy EPDM feed aliases from a template feed map.
- `template_config_dict()`: Return a stable JSON-like dictionary for hashing/reporting.

---

### 文件模块: `template_flowsheet.py`
**技术描述**: Template-aware process flowsheet adapter.

**核心技术类 (Classes)**:
- `TemplateFlowsheetResult`: Template-aware flowsheet result.

**核心技术函数接口 (Functions)**:
- `run_epdm_flowsheet_adapter()`: Run the established EPDM flowsheet and wrap it in the template contract.
- `run_template_flowsheet()`: Run a template-aware flowsheet.
- `template_stream_table()`: Return a stream table for either template or legacy flowsheet results.
- `template_unit_table()`: Return a unit-operation table for either template or legacy flowsheet results.
- `template_mass_balance_from_streams()`: Return mass-balance closure error percent for a simplified template split.
- `template_mass_balance()`: Return template-aware mass-balance summary.
- `template_flowsheet_dataframe()`: Return a compact report dataframe for the template flowsheet.

---

### 文件模块: `template_ode_rhs.py`
**技术描述**: Template-native ODE right-hand side for dynamic polymerization reactors.

**核心技术类 (Classes)**:
- `TemplateODERHSContext`: Inputs needed by the template ODE RHS.

**核心技术函数接口 (Functions)**:
- `build_template_ode_context()`: Build a physically bounded RHS context from a process-like config.
- `initial_template_ode_state()`: Create a non-negative initial state for template ODE integration.
- `template_ode_rhs()`: Return dy/dt for a template semi-batch polymerization reactor.
- `project_template_state()`: Project a flat state vector onto finite physical bounds.

---

### 文件模块: `thermo.py`
**技术描述**: Simplified thermodynamic models and optional thermo package detection.

**核心技术类 (Classes)**:
- `FlashSplit`: Flash calculation result.
- `ThermoEngine`: Thermodynamics facade with a stable simple-mode fallback.

**核心技术函数接口 (Functions)**:
- `thermo_package_available()`: Return True if the optional thermo package can be imported.
- `wilson_k_value()`: Estimate K value using Wilson correlation.
- `rachford_rice_residual()`: Rachford-Rice residual for a vapor fraction.
- `solve_rachford_rice()`: Solve Rachford-Rice equation and return vapor fraction in [0, 1].
- `mixture_cp_liq()`: Return mass-weighted liquid heat capacity in kJ/kg/K.

---

### 文件模块: `thermo_calibration.py`
**技术描述**: Thermodynamic calibration helpers for Henry and flash correction factors.

**核心技术类 (Classes)**:
- `ThermoCalibrationResult`: Thermodynamic calibration output for report/model-audit use.

**核心技术函数接口 (Functions)**:
- `thermo_calibration_metrics()`: Return MAE/RMSE/R2 for thermo calibration residuals.
- `save_thermo_calibration_result()`: Persist a calibrated thermodynamic set without modifying defaults.
- `calibrate_henry_from_data()`: Fit a Henry reference coefficient using existing solubility utility.
- `calibrate_flash_k_correction()`: Fit a scalar K-value correction from observed/predicted vapor recovery.
- `thermo_calibration_score()`: Return a bounded score summarizing thermo calibration completeness.

---

### 文件模块: `thermo_consistency.py`
**技术描述**: Thermodynamic sanity and phase-split consistency checks.

**核心技术类 (Classes)**:
- `ThermoConsistencyResult`: One thermo consistency check.

**核心技术函数接口 (Functions)**:
- `thermo_consistency_dataframe()`: Return thermo consistency checks as a DataFrame.
- `run_thermo_consistency_checks()`: Run default EOS, Henry and flash trend checks.
- `thermo_physical_constraints_dataframe()`: Return V5.3 thermodynamic physical-constraint checks.

---

### 文件模块: `time_series_data.py`
**技术描述**: Experimental time-series data import and validation.

**核心技术类 (Classes)**:
- `TimeSeriesValidationResult`: Validation result for experimental dynamic profiles.

**核心技术函数接口 (Functions)**:
- `load_time_series_csv_or_excel()`: Load an experimental profile from CSV or Excel.
- `validate_time_series_schema()`: Validate dynamic profile columns, monotonic time and finite key values.
- `normalize_time_series()`: Return a copy with known numeric columns converted to numeric dtype.

---

### 文件模块: `transport_core.py`
**技术描述**: Transport and heat-transfer math-core checks.

**核心技术类 (Classes)**:
- `TransportCoreCheck`: One transport-core trend or bound check.

**核心技术函数接口 (Functions)**:
- `pressure_drop_laminar_kPa()`: Return laminar Hagen-Poiseuille pressure drop proxy in kPa.
- `cooling_capacity_kW()`: Return positive cooling capacity in kW.
- `run_transport_core_checks()`: Run deterministic rheology, pressure-drop and heat-transfer trend checks.
- `transport_physical_constraints_dataframe()`: Return V5.3 transport physical-constraint gate results.

---

### 文件模块: `ui_audit.py`
**技术描述**: Static UI workflow audit helpers.

**核心技术类 (Classes)**:
- `UIAuditResult`: One UI/static-code audit item.

**核心技术函数接口 (Functions)**:
- `audit_file()`: Audit one Python UI file for accidental heavy work on page load.
- `run_ui_audit()`: Run the lightweight static UI audit.
- `ui_audit_dataframe()`: Return audit results as a DataFrame.

---

### 文件模块: `ui_theme.py`
**技术描述**: High-end industrial digital-twin UI theme helpers for Streamlit.

**核心技术函数接口 (Functions)**:
- `apply_theme()`: Apply the Android/Material-inspired industrial digital-twin theme.
- `install_safe_alerts()`: Install alert helpers that do not depend on Streamlit's optional emoji module.
- `top_bar()`: Render a glass top navigation bar.
- `kpi_grid()`: Render a responsive KPI card grid.
- `section_title()`: Render a section title in the digital-twin style.
- `status_color()`: Map a process/risk status to a digital-twin accent color.
- `risk_chip()`: Return an inline HTML status chip.

---

### 文件模块: `ui_workflow.py`
**技术描述**: UI action registry for explicit, efficient task triggering.

**核心技术类 (Classes)**:
- `UIAction`: A user-facing action and its computational side effects.

**核心技术函数接口 (Functions)**:
- `load_ui_actions()`: Return the built-in UI action registry.
- `get_ui_action()`: Return one UI action.
- `ui_actions_dataframe()`: Return UI actions as a DataFrame.
- `ui_registry_usability_dataframe()`: Return usability and de-duplication checks for the UI action registry.

---

### 文件模块: `uncertainty.py`
**技术描述**: Model-confidence and uncertainty analysis for EPDM digital-twin KPIs.

**核心技术类 (Classes)**:
- `UncertaintyResult`: Monte Carlo/LHS uncertainty analysis output.

**核心技术函数接口 (Functions)**:
- `run_uncertainty_analysis()`: Run a lightweight uncertainty analysis around the current flowsheet.

---

### 文件模块: `unitops.py`
**技术描述**: Unit operation abstractions for the EPDM process flowsheet.

**核心技术类 (Classes)**:
- `UnitOperation`: Base class for process unit operation blocks.
- `Mixer`: Mixer block that combines material streams.
- `Heater`: Preheater block with constant-Cp heat-duty estimate.
- `Reactor`: Polymerization reactor block wrapper.
- `Quench`: Catalyst deactivation/quench block.
- `FlashUnit`: Flash block wrapper.
- `Splitter`: Simple fraction splitter, useful for purge/recycle blocks.
- `RecycleBlock`: Simplified recycle accounting block without rigorous tear-stream iteration.

---

### 文件模块: `units.py`
**技术描述**: Unit conversion and dimensional sanity checks.

**核心技术函数接口 (Functions)**:
- `kg_h_to_mol_h()`: Convert kg/h to mol/h.
- `mol_h_to_kg_h()`: Convert mol/h to kg/h.
- `mol_L_to_mol_m3()`: Convert mol/L to mol/m3.
- `mol_m3_to_mol_L()`: Convert mol/m3 to mol/L.
- `mpa_to_pa()`: Convert MPa to Pa.
- `pa_to_mpa()`: Convert Pa to MPa.
- `c_to_k()`: Convert Celsius to Kelvin.
- `k_to_c()`: Convert Kelvin to Celsius.
- `l_to_m3()`: Convert L to m3.
- `m3_to_l()`: Convert m3 to L.
- `kj_h_to_kw()`: Convert kJ/h to kW.
- `kw_to_kj_h()`: Convert kW to kJ/h.
- `g_mol_to_kg_mol()`: Convert g/mol to kg/mol.
- `kg_mol_to_g_mol()`: Convert kg/mol to g/mol.
- `wt_percent_to_fraction()`: Convert wt% to mass fraction.
- `fraction_to_wt_percent()`: Convert mass fraction to wt%.
- `assert_temperature_K()`: Assert an absolute temperature is physically valid.
- `assert_pressure_Pa()`: Assert a pressure is positive.
- `assert_mass_flow_nonnegative()`: Assert a mass flow is non-negative.
- `assert_mole_fraction_sum()`: Assert mole fractions sum to one within tolerance.
- `assert_weight_percent_sum()`: Assert weight percentages sum to 100 within tolerance.
- `assert_heat_duty_sign()`: Assert heat-duty sign convention.
- `assert_conversion_range()`: Assert conversion lies in [0,1] or [0,100].
- `relative_error()`: Return a stable relative error.

---

### 文件模块: `utils.py`
**技术描述**: Shared utilities and unit conversions for the EPDM simulator.

**核心技术函数接口 (Functions)**:
- `data_path()`: Return an absolute path inside the project data directory.
- `load_json()`: Load JSON from a local file.
- `load_yaml()`: Load YAML from a local file.
- `write_json()`: Write JSON using UTF-8 encoding.
- `clamp()`: Clamp a numeric value to a closed interval.
- `positive()`: Return value if finite and above floor, otherwise floor.
- `safe_divide()`: Divide with a stable default for near-zero denominators.
- `kg_h_to_mol_h()`: Convert kg/h to mol/h using molecular weight in g/mol.
- `mol_h_to_kg_h()`: Convert mol/h to kg/h using molecular weight in g/mol.
- `normalize()`: Normalize non-negative mapping values to sum to one.
- `weighted_average()`: Return a weighted average across common keys.
- `c_to_k()`: Convert Celsius to Kelvin.
- `k_to_c()`: Convert Kelvin to Celsius.
- `mpa_to_pa()`: Convert MPa to Pa.
- `pa_to_mpa()`: Convert Pa to MPa.
- `mid_range()`: Return midpoint of a numeric range.
- `engineering_error_percent()`: Return signed percentage closure error with stable near-zero handling.
- `model_dump_compat()`: Return a Pydantic model dict in a v1/v2 compatible way.

---

### 文件模块: `validation_campaign.py`
**技术描述**: Engineering validation-campaign closure utilities.

**核心技术类 (Classes)**:
- `ValidationCampaignResult`: Validation campaign scorecard.

**核心技术函数接口 (Functions)**:
- `load_validation_datasets()`: Load validation dataset definitions from data/validation_datasets.json.
- `validation_datasets_dataframe()`: Return configured validation datasets as a table.
- `run_validation_campaign()`: Compare endpoint validation data to current model predictions.
- `recommend_next_validation_data()`: Recommend next validation data based on observed model bias.

---

### 文件模块: `validation_evidence.py`
**技术描述**: Evidence tables for model validation and audit confidence.

**核心技术函数接口 (Functions)**:
- `evidence_weight()`: Return source-type evidence weight with plant as strongest evidence.
- `validation_evidence_dataframe()`: Return benchmark/data-lineage evidence rows.

---

### 文件模块: `validity_envelope.py`
**技术描述**: Model validity-envelope checks for extrapolation governance.

**核心技术类 (Classes)**:
- `ValidityEnvelopeResult`: One validity-envelope classification row.

**核心技术函数接口 (Functions)**:
- `registry_validity_ranges()`: Return numeric validity ranges parsed from model_registry plus defaults.
- `template_validity_ranges()`: Return validity ranges declared by the reaction template.
- `check_value_against_range()`: Classify one value against a numeric range.
- `run_validity_envelope_for_config()`: Evaluate validity-envelope status for a process configuration.
- `property_source_validity_envelope()`: Return property-source range checks for the current T/P point.
- `validity_envelope_dataframe()`: Return validity-envelope results as a DataFrame.
- `validity_score()`: Return a 0-100 score penalizing near-edge and outside extrapolation.

---

### 文件模块: `workflow_wizard.py`
**技术描述**: R&D workflow wizard metadata and next-action guidance.

**核心技术类 (Classes)**:
- `WorkflowStep`: One workflow wizard step.

**核心技术函数接口 (Functions)**:
- `load_workflow_steps()`: Return the V4.7 R&D workflow steps.
- `workflow_status()`: Return wizard step status without running heavy tasks.
- `next_recommended_action()`: Return the next unfinished workflow action id.

---

### 文件模块: `cfd\boundary.py`
**技术描述**: Boundary-condition objects for lightweight CFD and OpenFOAM export.

**核心技术类 (Classes)**:
- `BoundaryCondition`: Simple CFD boundary-condition descriptor.

**核心技术函数接口 (Functions)**:
- `default_pipe_boundaries()`: Return consistent pipe BC names for the FVM and OpenFOAM skeleton.

---

### 文件模块: `cfd\fem_solver.py`
**技术描述**: Optional FEniCSx solver facade.

**核心技术函数接口 (Functions)**:
- `fenicsx_available()`: Return True when dolfinx appears importable.
- `selected_solver_mode()`: Return the actual CFD solver mode used by the application.

---

### 文件模块: `cfd\fields.py`
**技术描述**: CFD field containers and scalar diagnostics.

**核心技术类 (Classes)**:
- `CFDFields`: Scalar and vector fields on a structured CFD mesh.
- `CFDDiagnostics`: Engineering diagnostics from the CFD-style fields.

**核心技术函数接口 (Functions)**:
- `masked_stats()`: Return min, max, mean and std on active mesh cells.
- `location_of_extreme()`: Return x,y location for a field maximum or minimum inside active cells.

---

### 文件模块: `cfd\fouling.py`
**技术描述**: Fouling-risk field calculations for EPDM CFD visualizations.

**核心技术函数接口 (Functions)**:
- `calculate_fouling_field()`: Calculate local wall/dead-zone/polymer fouling risk index.
- `risk_level()`: Return qualitative fouling-risk class.

---

### 文件模块: `cfd\grid_convergence.py`
**技术描述**: CFD scalar-label and grid-convergence diagnostics.

**核心技术类 (Classes)**:
- `CFDGridConvergenceResult`: Grid-convergence metrics for selected CFD mesh sizes.

**核心技术函数接口 (Functions)**:
- `scalar_labels_from_template()`: Return CFD scalar labels from reaction-template monomers.
- `run_cfd_grid_convergence()`: Run a lightweight grid convergence sweep.

---

### 文件模块: `cfd\mesh.py`
**技术描述**: Structured 2D meshes for lightweight CFD visualizations.

**核心技术类 (Classes)**:
- `CFDGeometryConfig`: Geometry and mesh settings for the simplified CFD module.
- `StructuredMesh`: Structured CFD mesh with active-cell mask and wall distance.

**核心技术函数接口 (Functions)**:
- `create_mesh()`: Create a structured 2D mesh for pipe, reactor section or annulus.

---

### 文件模块: `cfd\openfoam_export.py`
**技术描述**: OpenFOAM case skeleton export for downstream industrial CFD.

**核心技术函数接口 (Functions)**:
- `generate_openfoam_case_files()`: Generate an OpenFOAM case skeleton as path-to-text mapping.
- `export_openfoam_case_zip()`: Return a zipped OpenFOAM case skeleton.

---

### 文件模块: `cfd\simple_solver.py`
**技术描述**: Built-in lightweight 2D CFD-style solver for EPDM process visualization.

**核心技术类 (Classes)**:
- `CFDInput`: Inputs for the lightweight CFD/FEM-style simulation.
- `SimpleCFDResult`: Result from the built-in CFD-style solver.

**核心技术函数接口 (Functions)**:
- `run_simple_cfd()`: Run the lightweight CFD-style solver and return fields and diagnostics.
- `run_pipe_fvm_solver()`: Run a finite-volume-style pipe calculation with pressure/T/ENB fields.
- `build_cfd_input_from_flowsheet()`: Create default CFD inputs coupled from a flowsheet result.

---

### 文件模块: `cfd\transport.py`
**技术描述**: Lightweight finite-volume-style transport utilities.

**核心技术函数接口 (Functions)**:
- `smooth_active_field()`: Diffuse/smooth a scalar field on active mesh cells using neighbor averaging.
- `apply_pipe_inlet_outlet()`: Apply simple pipe inlet, outlet and optional wall scalar boundary conditions.
- `normalized_active()`: Normalize active field values to [0, 1].

---

### 文件模块: `cfd\visualization.py`
**技术描述**: Plotly visualization helpers for CFD/FEM-style results.

**核心技术函数接口 (Functions)**:
- `mesh_plot()`: Return a structured mesh plot.
- `contour_plot()`: Return a contour plot for a named CFD field.
- `velocity_vector_plot()`: Return a 2D velocity vector/quiver style plot.
- `streamline_plot()`: Return a finite-element style streamline visualization.
- `surface_plot()`: Return a quasi-3D surface plot for a named field.
- `reactor_cfd_3d_view()`: Return an enhanced 3D stirred-tank view with an internal CFD slice.
- `export_legacy_vtk()`: Export CFD fields as an ASCII legacy VTK structured grid file.

---

### 文件模块: `dynamic_core\adaptive_integrator.py`
**技术描述**: Adaptive integrator audit helpers for V6.4 dynamic models.

**核心技术函数接口 (Functions)**:
- `integrate_with_adaptive_policy()`: Return adaptive integration status without rerunning heavy dynamics.
- `adaptive_integrator_dataframe()`: Return adaptive integrator step rows.
- `adaptive_integrator_summary()`: Return compact adaptive integrator status.
- `adaptive_integrator_gate()`: Return release-gate status for adaptive integrator diagnostics.

---

### 文件模块: `dynamic_core\adaptive_step_control.py`
**技术描述**: Adaptive step-control diagnostics for V6.3 dynamic models.

**核心技术函数接口 (Functions)**:
- `adaptive_step_decision()`: Return one adaptive accept/reject decision.
- `adaptive_step_control_dataframe()`: Return adaptive step-control table from dynamic step acceptance.
- `adaptive_step_control_summary()`: Return compact adaptive step statistics.

---

### 文件模块: `dynamic_core\dae_constraints.py`
**技术描述**: DAE-style dynamic constraints for V6.0 state diagnostics.

**核心技术函数接口 (Functions)**:
- `dae_constraints_dataframe()`: Return DAE/state algebraic constraint checks for a dynamic profile.
- `dae_constraints_status()`: Return compact DAE constraints status.

---

### 文件模块: `dynamic_core\event_certificates.py`
**技术描述**: Dynamic event certificate helpers.

**核心技术函数接口 (Functions)**:
- `event_certificate()`: Return an event certificate row.
- `event_certificate_dataframe()`: Return event certificates for dynamic profile governance.

---

### 文件模块: `dynamic_core\event_detection.py`
**技术描述**: Dynamic event detection helpers for V6.3.

**核心技术函数接口 (Functions)**:
- `detect_dynamic_events()`: Detect quench, cooling-failure and runaway-style events from a profile.
- `dynamic_event_detection_dataframe()`: Return dynamic event detection rows.
- `event_flags_summary()`: Return compact event flags for solver policy.

---

### 文件模块: `dynamic_core\event_localization.py`
**技术描述**: Dynamic event localization helpers for V6.4.

**核心技术函数接口 (Functions)**:
- `localize_dynamic_events()`: Return approximate event localization windows from event diagnostics.
- `event_localization_dataframe()`: Return event localization rows.
- `event_localization_summary()`: Return compact event localization status.
- `event_localization_gate()`: Return release-gate status for event localization.

---

### 文件模块: `dynamic_core\invariant_projection.py`
**技术描述**: Dynamic state invariant projection helpers.

**核心技术函数接口 (Functions)**:
- `project_state_invariants()`: Project inventory/T/P states into basic nonnegative invariants.
- `invariant_projection_dataframe()`: Return invariant projection as rows.

---

### 文件模块: `dynamic_core\residual_feedback.py`
**技术描述**: Feed dynamic residuals back into solver diagnostics and fallback policy.

**核心技术函数接口 (Functions)**:
- `dynamic_residual_feedback()`: Return residual severity rows for a dynamic result.
- `residual_feedback_solver_status()`: Return solver status augmented with residual acceptance diagnostics.
- `residual_feedback_recommends_fallback()`: Return whether residual feedback should recommend solver fallback/warning.

---

### 文件模块: `dynamic_core\residual_timeseries.py`
**技术描述**: Dynamic residual time-series helpers for report and gates.

**核心技术函数接口 (Functions)**:
- `dynamic_residual_timeseries()`: Return residual rows with a V5.5 coupling status column.
- `dynamic_rhs_residual_acceptance()`: Return combined residual and RHS-term acceptance.

---

### 文件模块: `dynamic_core\rhs_terms.py`
**技术描述**: RHS term diagnostics coupled to template ODE state derivatives.

**核心技术类 (Classes)**:
- `RHSTerm`: One physically labelled RHS contribution.

**核心技术函数接口 (Functions)**:
- `rhs_terms_for_state()`: Return labelled RHS derivative terms for one state vector.
- `rhs_term_schema()`: Return the expected RHS term schema without running a model.
- `rhs_terms_from_profile()`: Return a lightweight RHS-coupling table from an existing profile.

---

### 文件模块: `dynamic_core\solver_decision.py`
**技术描述**: Residual-aware dynamic solver decision helpers for V6.1.

**核心技术函数接口 (Functions)**:
- `choose_dynamic_solver()`: Choose RK45/BDF/explicit fallback from stiffness, residuals and events.
- `dynamic_fallback_policy()`: Return fallback policy from dynamic solver status fields.
- `residual_based_step_acceptance()`: Accept/reject one dynamic step based on residual error.
- `dynamic_solver_decision_dataframe()`: Return solver decision rows for report/release gates.

---

### 文件模块: `dynamic_core\solver_policy.py`
**技术描述**: Closed-loop dynamic solver policy for V6.2.

**核心技术函数接口 (Functions)**:
- `choose_dynamic_solver_policy()`: Choose dynamic solver policy from stiffness, residuals, invariants and events.
- `dynamic_solver_policy_dataframe()`: Return dynamic solver policy rows.
- `dynamic_solver_policy_report()`: Return compact report-safe dynamic solver policy status.

---

### 文件模块: `dynamic_core\stability_checks.py`
**技术描述**: Proof-style dynamic stability checks for template ODE profiles.

**核心技术函数接口 (Functions)**:
- `dynamic_stability_checks_dataframe()`: Return finite, monotonic and residual-feedback stability checks.
- `dynamic_stability_status()`: Return compact stability status for release gates.
- `stiffness_indicator_from_profile()`: Return a lightweight stiffness indicator from T/P gradients.

---

### 文件模块: `dynamic_core\state_invariants.py`
**技术描述**: Dynamic state invariant checks for V6.0.

**核心技术函数接口 (Functions)**:
- `state_invariants_dataframe()`: Return monotonicity, positivity and quench invariant checks.
- `state_invariants_status()`: Return compact state invariant status.

---

### 文件模块: `dynamic_core\step_acceptance.py`
**技术描述**: Dynamic step acceptance helpers for V6.2 solver policy.

**核心技术函数接口 (Functions)**:
- `dynamic_step_acceptance_record()`: Return one bounded step-acceptance decision.
- `dynamic_step_acceptance_dataframe()`: Return step acceptance rows from dynamic residual feedback.
- `dynamic_step_acceptance_summary()`: Return compact step acceptance statistics.

---

### 文件模块: `estimation\confidence.py`
**技术描述**: Confidence interval helpers for fitted parameters.

**核心技术函数接口 (Functions)**:
- `confidence_interval_dataframe()`: Return quantile confidence intervals for parameter samples.

---

### 文件模块: `estimation\constraints.py`
**技术描述**: Parameter-constraint tables for calibration workflows.

**核心技术函数接口 (Functions)**:
- `estimation_parameter_constraints()`: Return physical parameter constraints for estimation.

---

### 文件模块: `estimation\fit_diagnostics.py`
**技术描述**: Fit diagnostics for residual-constrained calibration.

**核心技术函数接口 (Functions)**:
- `fit_diagnostics_record()`: Return finite/bounded diagnostics for a fit result.
- `fit_diagnostics_dataframe()`: Return a report-safe fit diagnostics table.

---

### 文件模块: `estimation\fit_runner.py`
**技术描述**: Small residual-aware fit runner facade.

**核心技术函数接口 (Functions)**:
- `run_fit_with_residual_constraints()`: Run the existing residual-constrained fit and expose a stable facade.
- `fit_runner_dataframe()`: Return one-row fit runner status.

---

### 文件模块: `estimation\objectives.py`
**技术描述**: Residual-aware objective helpers for calibration.

**核心技术函数接口 (Functions)**:
- `residual_aware_parameter_objective()`: Combine data residual and physical residual penalty.

---

### 文件模块: `estimation\persistence.py`
**技术描述**: Calibration persistence metadata helpers.

**核心技术函数接口 (Functions)**:
- `calibrated_set_record()`: Return a non-mutating calibrated parameter-set record.

---

### 文件模块: `estimation\physical_penalties.py`
**技术描述**: Physical penalty terms for residual-constrained estimation.

**核心技术函数接口 (Functions)**:
- `physical_penalty()`: Return a quadratic penalty outside physical bounds.
- `physical_penalty_breakdown()`: Return parameter-level physical penalties.

---

### 文件模块: `estimation\residuals.py`
**技术描述**: Data residual helpers for parameter estimation.

**核心技术函数接口 (Functions)**:
- `parameter_residual_dataframe()`: Return observed-predicted residual rows with units.

---

### 文件模块: `estimation\residual_constrained_fit.py`
**技术描述**: Residual-constrained parameter-estimation helpers for V5.6.

**核心技术类 (Classes)**:
- `ResidualConstrainedFitResult`: Small audit object for residual-constrained fitting.

**核心技术函数接口 (Functions)**:
- `validate_target_units()`: Return unit errors for parameter-estimation targets.
- `parameter_prior_penalty()`: Return a bounded penalty for parameters outside physical constraints.
- `residual_constrained_objective()`: Return data residual plus physical-residual, prior and unit penalties.
- `run_residual_constrained_fit()`: Build a deterministic residual-constrained fit audit result.
- `residual_constrained_fit_dataframe()`: Return a compact report table for residual-constrained fitting.

---

### 文件模块: `estimation\residual_objectives.py`
**技术描述**: Residual-objective helpers split from parameter-estimation workflows.

**核心技术函数接口 (Functions)**:
- `weighted_data_residual()`: Return a unit-tagged squared data residual.
- `combined_residual_objective()`: Combine data residuals with physical residual objective.
- `residual_objectives_dataframe()`: Return objective audit rows.

---

### 文件模块: `flowsheet_core\energy_closure.py`
**技术描述**: Flowsheet energy-closure helpers.

**核心技术函数接口 (Functions)**:
- `energy_closure_record()`: Return energy closure for exothermic reaction and cooling duty.
- `energy_closure_dataframe()`: Return energy closure as a DataFrame.

---

### 文件模块: `flowsheet_core\feed_builder.py`
**技术描述**: Template feed-building helpers.

**核心技术函数接口 (Functions)**:
- `build_feed_from_template_config()`: Build a feed stream from a template process config.

---

### 文件模块: `flowsheet_core\kpi_builder.py`
**技术描述**: Template KPI builder wrappers.

**核心技术函数接口 (Functions)**:
- `build_kpis_for_template()`: Build template-aware KPIs from a flowsheet result.

---

### 文件模块: `flowsheet_core\kpi_projection.py`
**技术描述**: KPI projection helpers with physical bounds.

**核心技术函数接口 (Functions)**:
- `project_kpis_with_bounds()`: Project selected KPI values into physical reporting bounds.
- `kpi_projection_dataframe()`: Return projected KPI table.

---

### 文件模块: `flowsheet_core\material_closure.py`
**技术描述**: Flowsheet material-closure helpers.

**核心技术函数接口 (Functions)**:
- `material_closure_record()`: Return material closure around flowsheet boundary.
- `material_closure_dataframe()`: Return material closure as a DataFrame.

---

### 文件模块: `flowsheet_core\recycle.py`
**技术描述**: Recycle closure helper wrappers.

**核心技术函数接口 (Functions)**:
- `recycle_closure_correction()`: Return bounded recycle closure correction.

---

### 文件模块: `flowsheet_core\residual_builder.py`
**技术描述**: Flowsheet residual builder wrappers.

**核心技术函数接口 (Functions)**:
- `build_flowsheet_residuals()`: Build a ResidualSystem from a flowsheet result.

---

### 文件模块: `flowsheet_core\unit_residuals.py`
**技术描述**: Unit-operation residual helpers.

**核心技术函数接口 (Functions)**:
- `unit_residuals_dataframe()`: Return default unit residual examples for release-gate schema.

---

### 文件模块: `flowsheet_core\unit_sequence.py`
**技术描述**: Flowsheet unit-sequence metadata.

**核心技术函数接口 (Functions)**:
- `default_unit_sequence()`: Return the default EPDM solution-polymerization unit sequence.

---

### 文件模块: `fluid_core\density.py`
**技术描述**: Density helpers.

**核心技术函数接口 (Functions)**:
- `density_kg_m3()`: Return density in kg/m3.

---

### 文件模块: `fluid_core\heat_capacity.py`
**技术描述**: Heat-capacity helpers.

**核心技术函数接口 (Functions)**:
- `mixture_heat_capacity_kJ_kgK()`: Return positive mass-weighted mixture heat capacity.

---

### 文件模块: `fluid_core\hydraulics.py`
**技术描述**: Hydraulic trend helpers.

**核心技术函数接口 (Functions)**:
- `darcy_pressure_drop_kPa()`: Return Darcy-Weisbach pressure drop in kPa.

---

### 文件模块: `fluid_core\property_selector_bridge.py`
**技术描述**: Fluid-core bridge to calibrated property selection.

**核心技术函数接口 (Functions)**:
- `fluid_property_bridge_dataframe()`: Return property-bridge rows for fluid calculations.

---

### 文件模块: `fluid_core\transport_residuals.py`
**技术描述**: Transport residual helpers for fluid-core split.

**核心技术函数接口 (Functions)**:
- `transport_residuals_dataframe()`: Return simple positive transport residual checks.

---

### 文件模块: `fluid_core\viscosity.py`
**技术描述**: Viscosity helpers.

**核心技术函数接口 (Functions)**:
- `viscosity_Pa_s()`: Return viscosity in Pa.s.

---

### 文件模块: `math_core\acceptance.py`
**技术描述**: Unified V5.7 model-acceptance helpers.

**核心技术函数接口 (Functions)**:
- `math_core_acceptance()`: Return combined equation/residual/constraint acceptance.
- `math_core_acceptance_dataframe()`: Return combined math-core acceptance as a one-row DataFrame.

---

### 文件模块: `math_core\balance_laws.py`
**技术描述**: Balance-law helpers for the V6.0 industrial math core.

**核心技术函数接口 (Functions)**:
- `accumulation_identity()`: Evaluate accumulation = input - output + generation - consumption.
- `balance_law_records()`: Return mass, component, phase, reaction and energy balance records.
- `balance_law_acceptance()`: Return compact balance-law acceptance diagnostics.

---

### 文件模块: `math_core\constraints.py`
**技术描述**: Physical-constraint aggregation for the V5.7 math core.

**核心技术函数接口 (Functions)**:
- `physical_constraints_dataframe()`: Return phase, transport and validity constraints in one table.
- `physical_constraints_acceptance()`: Return pass/fail summary for aggregated physical constraints.

---

### 文件模块: `math_core\diagnostics.py`
**技术描述**: Top-level diagnostics for the layered V5.7 math core.

**核心技术函数接口 (Functions)**:
- `math_core_diagnostics_dataframe()`: Return compact diagnostics across equations, residuals and constraints.

---

### 文件模块: `math_core\dimension_signatures.py`
**技术描述**: Dimension-signature validation for equation registry records.

**核心技术函数接口 (Functions)**:
- `dimension_signature_dataframe()`: Return equation dimensional signatures and unit completeness flags.
- `validate_dimension_signatures()`: Return compact dimension-signature gate status.

---

### 文件模块: `math_core\equations.py`
**技术描述**: Equation-level math-kernel summaries.

**核心技术函数接口 (Functions)**:
- `equation_kernel_dataframe()`: Return equation binding rows with reverse-check status.
- `equation_kernel_acceptance()`: Return release-gate style equation acceptance summary.

---

### 文件模块: `math_core\equation_graph.py`
**技术描述**: Equation graph helpers for the V6.0 math core.

**核心技术函数接口 (Functions)**:
- `equation_graph_dataframe()`: Return graph-style edges from equation to implementation/residual/benchmark.
- `equation_graph_acceptance()`: Return compact equation graph acceptance status.

---

### 文件模块: `math_core\kinetic_identities.py`
**技术描述**: Kinetic identity helpers for V6.0 release gates.

**核心技术函数接口 (Functions)**:
- `arrhenius_rate_ratio()`: Return k_high/k_low for the same pre-exponential factor.
- `eyring_rate_constant()`: Return k = kB T / h * exp(-deltaG^‡ / RT).
- `kinetic_identity_checks_dataframe()`: Return finite/trend checks for Arrhenius and Eyring identities.

---

### 文件模块: `math_core\model_confidence.py`
**技术描述**: V6.0 math-core confidence composition helpers.

**核心技术函数接口 (Functions)**:
- `combine_confidence_components()`: Return a bounded weighted confidence score.
- `model_confidence_kernel_dataframe()`: Return default model-confidence components for report/gate use.

---

### 文件模块: `math_core\residuals.py`
**技术描述**: Residual-level math-kernel helpers.

**核心技术函数接口 (Functions)**:
- `coerce_residual_system()`: Return a residual system from a result or residual-system object.
- `residual_kernel_dataframe()`: Return detailed residual diagnostics for math-core gates.
- `residual_kernel_acceptance()`: Return residual acceptance with objective penalty.

---

### 文件模块: `math_core\residual_graph.py`
**技术描述**: Residual graph helpers for the V6.0 math core.

**核心技术函数接口 (Functions)**:
- `residual_graph_dataframe()`: Return graph-style residual -> source/fix rows.
- `residual_graph_acceptance()`: Return compact residual graph acceptance status.

---

### 文件模块: `math_core\thermodynamic_identities.py`
**技术描述**: Thermodynamic identities used by V6.0 science gates.

**核心技术函数接口 (Functions)**:
- `gibbs_from_enthalpy_entropy()`: Return delta G = delta H - T delta S in J/mol.
- `equilibrium_constant_from_delta_g()`: Return K = exp(-deltaG / RT).
- `delta_g_from_equilibrium_constant()`: Return delta G = -RT ln K in J/mol.
- `thermodynamic_identity_checks_dataframe()`: Return deterministic identity checks without running heavy models.

---

### 文件模块: `pages\calibration_page.py`
**技术描述**: Parameter set management and nonlinear estimation page components.

**核心技术函数接口 (Functions)**:
- `render_parameter_management()`: Render parameter-set registry and nonlinear estimation controls.

---

### 文件模块: `pages\case_manager_page.py`
**技术描述**: Case and scenario management page.

**核心技术函数接口 (Functions)**:
- `render_case_manager_page()`: Render case save/load/compare UI.

---

### 文件模块: `pages\cfd_page.py`
**技术描述**: CFD/FEM-style visualization page.

**核心技术函数接口 (Functions)**:
- `render_cfd_page()`: Render manually triggered CFD-style fields and diagnostics.

---

### 文件模块: `pages\dashboard_page.py`
**技术描述**: Digital-twin dashboard page.

**核心技术函数接口 (Functions)**:
- `render_dashboard_page()`: Render the fast digital-twin overview without heavy recomputation.

---

### 文件模块: `pages\dynamic_reactor_page.py`
**技术描述**: Dynamic batch/semi-batch reactor page.

**核心技术函数接口 (Functions)**:
- `render_dynamic_reactor_page()`: Render dynamic stirred-tank timelines with manual ODE trigger.

---

### 文件模块: `pages\equipment_library_page.py`
**技术描述**: 3D equipment library page.

**核心技术函数接口 (Functions)**:
- `render_equipment_library_page()`: Render individual equipment sketches and metadata.

---

### 文件模块: `pages\experiment_data_page.py`
**技术描述**: Experiment data management page.

**核心技术函数接口 (Functions)**:
- `render_experiment_data_page()`: Render experiment data import, normalization and quality diagnostics.

---

### 文件模块: `pages\heat_fluid_page.py`
**技术描述**: Heat balance, fluid properties and safety page.

**核心技术函数接口 (Functions)**:
- `render_heat_fluid_page()`: Render energy, fluid-property, hydraulics and thermal safety diagnostics.

---

### 文件模块: `pages\model_governance_page.py`
**技术描述**: Model governance and confidence-certificate page.

**核心技术函数接口 (Functions)**:
- `render_model_governance_page()`: Render read-only governance diagnostics without triggering heavy tasks.

---

### 文件模块: `pages\product_page.py`
**技术描述**: Product properties and target-grade matching page.

**核心技术函数接口 (Functions)**:
- `render_product_page()`: Render product-property prediction and Vistalon-like benchmarking.

---

### 文件模块: `pages\reactor_page.py`
**技术描述**: Reactor and kinetics page.

**核心技术函数接口 (Functions)**:
- `render_reactor_page()`: Render reactor, kinetics and gas-liquid concentration diagnostics.

---

### 文件模块: `pages\report_page.py`
**技术描述**: Report export page.

**核心技术函数接口 (Functions)**:
- `render_report_page()`: Render report export controls without rerunning heavy calculations.

---

### 文件模块: `pages\sensitivity_optimization_page.py`
**技术描述**: Sensitivity, single-objective optimization and Pareto page.

**核心技术函数接口 (Functions)**:
- `render_sensitivity_optimization_page()`: Render on-demand sensitivity, optimization and Pareto calculations.

---

### 文件模块: `pages\separation_page.py`
**技术描述**: Separation, flash, recycle and thermodynamics page.

**核心技术函数接口 (Functions)**:
- `render_separation_page()`: Render thermodynamics, flash split and recycle diagnostics.

---

### 文件模块: `pages\workflow_wizard_page.py`
**技术描述**: Streamlit page for the V4.7 R&D workflow wizard.

**核心技术函数接口 (Functions)**:
- `render_page()`: Render workflow guidance without triggering heavy models.

---

### 文件模块: `reactor_core\heat_release.py`
**技术描述**: Reactor heat-release helper equations.

**核心技术函数接口 (Functions)**:
- `heat_release_from_conversion()`: Return exothermic heat release in kW from consumed monomer.
- `heat_release_dataframe()`: Return heat-release record as a DataFrame.

---

### 文件模块: `reactor_core\material_balance.py`
**技术描述**: Reactor material-balance helpers.

**核心技术函数接口 (Functions)**:
- `consumed_monomer_mass_kg_h()`: Return total consumed monomer mass in kg/h.

---

### 文件模块: `reactor_core\polymer_moments.py`
**技术描述**: Polymer moment sanity helpers.

**核心技术函数接口 (Functions)**:
- `polymer_moment_estimates()`: Return bounded Mn/Mw/PDI estimates.
- `polymer_moments_dataframe()`: Return polymer moments as a DataFrame.

---

### 文件模块: `reactor_core\rate_engine.py`
**技术描述**: Template rate-engine wrapper.

**核心技术函数接口 (Functions)**:
- `template_rate_engine()`: Return nonnegative template rates in mol/L/h.

---

### 文件模块: `reactor_core\reaction_balance.py`
**技术描述**: Reactor material-balance helpers.

**核心技术函数接口 (Functions)**:
- `reaction_mass_balance_record()`: Return a simple reactor mass balance record.
- `reaction_balance_dataframe()`: Return reactor balance as a DataFrame.

---

### 文件模块: `reactor_core\reactor_outputs.py`
**技术描述**: Reactor output table helpers.

**核心技术函数接口 (Functions)**:
- `reactor_output_dataframe()`: Return reactor KPI dictionary as a table.

---

### 文件模块: `reactor_core\reactor_residuals.py`
**技术描述**: Reactor residual report helpers.

**核心技术函数接口 (Functions)**:
- `reactor_residuals_dataframe()`: Return reactor residual rows.

---

### 文件模块: `reactor_core\stoichiometry.py`
**技术描述**: Stoichiometry helpers for template polymerization.

**核心技术函数接口 (Functions)**:
- `monomer_segment_map()`: Return template monomer-to-segment stoichiometry map.

---

### 文件模块: `reporting\excel.py`
**技术描述**: Excel report export module.

**核心技术函数接口 (Functions)**:
- `export_excel()`: Build an Excel workbook containing streams, units and KPI tables.

---

### 文件模块: `reporting\pdf.py`
**技术描述**: PDF report export module.

**核心技术函数接口 (Functions)**:
- `export_pdf_report()`: Build a compact PDF report with assumptions, inputs and key results.

---

### 文件模块: `reporting\word.py`
**技术描述**: Word report export module.

**核心技术函数接口 (Functions)**:
- `export_word_report()`: Build a Word report including heat balance and fluid property tables.

---

### 文件模块: `services\cache_keys.py`
**技术描述**: Stable cache-key helpers for simulation services.

**核心技术函数接口 (Functions)**:
- `stable_json_dumps()`: Return deterministic JSON for cache and case fingerprints.
- `hash_payload()`: Return a short stable SHA1 hash for a payload.
- `config_cache_key()`: Return the flowsheet cache key for a process configuration.
- `detail_cache_key()`: Return a cache key for detail calculations such as CFD or ODE.
- `model_fingerprint()`: Return a compact fingerprint for multiple model inputs.

---

### 文件模块: `services\report_service.py`
**技术描述**: Report export service and Plotly image fallback helpers.

**核心技术函数接口 (Functions)**:
- `export_bundle()`: Export one report type without rerunning expensive models.
- `figure_export_status()`: Return static image export readiness notes for Plotly figures.

---

### 文件模块: `services\simulation_service.py`
**技术描述**: Simulation orchestration service used by Streamlit pages.

**核心技术类 (Classes)**:
- `TimedResult`: Result object plus wall-clock runtime metadata.

**核心技术函数接口 (Functions)**:
- `process_config_from_payload()`: Normalize a configuration payload into ProcessConfig.
- `run_flowsheet_with_store()`: Run or reuse a fast flowsheet result from a ResultsStore-like object.
- `stale_flags()`: Return stale flags for fast and detail calculations.
- `performance_rows()`: Return rows for the UI performance diagnostics expander.

---

### 文件模块: `services\task_service.py`
**技术描述**: Lightweight long-task status service for Streamlit session state.

**核心技术类 (Classes)**:
- `TaskRecord`: State record for one manually triggered long task.
- `TaskService`: In-process task status manager backed by a dictionary/session_state.

**核心技术函数接口 (Functions)**:
- `task_graph_dataframe()`: Return the high-level task graph as a DataFrame for UI diagnostics.

---

### 文件模块: `solver_core\bounded_solver.py`
**技术描述**: Bounded numerical update helpers.

**核心技术函数接口 (Functions)**:
- `project_nonnegative()`: Project finite numeric values to a nonnegative lower bound.
- `bounded_explicit_step()`: Return one explicit step with finite nonnegative projection.

---

### 文件模块: `solver_core\conservation_correction.py`
**技术描述**: Small-balance correction certificates for V6.1 conservation gates.

**核心技术函数接口 (Functions)**:
- `close_small_mass_residual()`: Close a small mass residual without hiding large conservation errors.
- `close_small_energy_residual()`: Close a small energy residual while rejecting sign/unit mistakes.
- `close_flash_split_residual()`: Adjust a tiny flash liquid split mismatch and reject large mismatch.
- `reject_large_residual_correction()`: Return whether a correction must be rejected as physically unsafe.
- `correction_certificate_dataframe()`: Return correction certificates for mass and energy residuals.

---

### 文件模块: `solver_core\conservation_jacobian.py`
**技术描述**: Finite-difference conservation Jacobian helpers for V6.3.

**核心技术函数接口 (Functions)**:
- `residual_vector_from_system()`: Return the residual absolute-error vector in project units.
- `estimate_conservation_jacobian()`: Estimate a finite-difference Jacobian for a residual function.
- `jacobian_condition_number()`: Return a finite condition number, with infinity for singular matrices.
- `conservation_jacobian_dataframe()`: Return a report-safe conservation Jacobian table.

---

### 文件模块: `solver_core\conservation_solve_path.py`
**技术描述**: Conservation-constrained solve-path helpers for V6.2.

**核心技术函数接口 (Functions)**:
- `apply_conservation_corrections_to_flowsheet()`: Apply accepted small residual corrections and return a solve certificate.
- `solve_flash_with_mass_closure()`: Close a small flash split mismatch while keeping polymer vapor critical.
- `solve_heat_balance_with_energy_closure()`: Close a small heat-balance residual and reject sign/unit mistakes.
- `solve_recycle_with_residual_acceptance()`: Return an accepted/rejected recycle closure correction.
- `conservation_solve_certificate_dataframe()`: Return V6.2 conservation solve-path certificate rows.

---

### 文件模块: `solver_core\constrained_solver.py`
**技术描述**: Constrained residual-aware solver helpers for V6.0.

**核心技术类 (Classes)**:
- `ConstrainedSolveResult`: Result from a bounded residual-constrained solve/certification pass.

**核心技术函数接口 (Functions)**:
- `minimize_residual_subject_to_bounds()`: Project a scalar into bounds and report residual penalty.
- `solve_with_mass_energy_constraints()`: Return a constrained solve certificate from existing residuals.
- `constrained_solver_dataframe()`: Return constrained solver status and certificate fields.

---

### 文件模块: `solver_core\dae_solver.py`
**技术描述**: Lightweight DAE constraint diagnostics for dynamic reactor results.

**核心技术函数接口 (Functions)**:
- `dae_solver_status()`: Return DAE/fallback status from dynamic state constraints.
- `dae_solver_dataframe()`: Return DAE solver status and constraints.

---

### 文件模块: `solver_core\equation_oriented_solver.py`
**技术描述**: Equation-oriented conservation solve helpers for V6.3.

**核心技术函数接口 (Functions)**:
- `build_conservation_equation_system()`: Return conservation equations and residuals as an equation system table.
- `bounded_residual_newton_step()`: Return one bounded least-squares Newton correction step.
- `solve_equation_oriented_residuals()`: Solve small conservation residuals with a bounded equation-oriented step.
- `equation_oriented_solver_certificate()`: Return equation-oriented solver certificate rows.
- `equation_oriented_solver_gate()`: Return compact V6.3 release-gate status.

---

### 文件模块: `solver_core\fallback_policy.py`
**技术描述**: Fallback policy helpers for residual-aware solvers.

**核心技术函数接口 (Functions)**:
- `fallback_policy_decision()`: Return whether a solver should warn/fallback from residual quality.

---

### 文件模块: `solver_core\nonlinear_residual_loop.py`
**技术描述**: Bounded nonlinear residual-loop helpers for V6.4.

**核心技术函数接口 (Functions)**:
- `build_flowsheet_residual_equations()`: Return the current flowsheet residual equations for nonlinear iteration.
- `bounded_physical_projection()`: Decide whether a bounded projection may be applied without hiding physics.
- `nonlinear_residual_iteration()`: Run a bounded residual-reduction loop and return iteration diagnostics.
- `residual_iteration_certificate()`: Return an auditable residual-iteration certificate.
- `nonlinear_residual_loop_gate()`: Return compact gate status for the nonlinear residual loop.

---

### 文件模块: `solver_core\residual_minimizer.py`
**技术描述**: Residual minimization helpers with bounded corrections.

**核心技术函数接口 (Functions)**:
- `enforce_phase_split_constraints()`: Return bounded phase-split closure diagnostics.
- `enforce_heat_balance_constraints()`: Return bounded heat-balance closure diagnostics.
- `residual_minimizer_dataframe()`: Return representative residual-minimization checks.

---

### 文件模块: `solver_core\residual_projection.py`
**技术描述**: Residual projection and acceptance helpers.

**核心技术函数接口 (Functions)**:
- `bounded_residual_projection()`: Apply a bounded correction and report whether it is physically small.
- `residual_projection_penalty()`: Return the residual objective score as a projection penalty.

---

### 文件模块: `solver_core\solver_certificates.py`
**技术描述**: Solver certificate generation for V6.0 audit reports.

**核心技术函数接口 (Functions)**:
- `generate_solver_certificate()`: Return a finite certificate for residual-aware solver acceptance.
- `solver_certificate_dataframe()`: Return solver certificate as a DataFrame.

---

### 文件模块: `solver_core\solver_status.py`
**技术描述**: Solver status tabulation helpers.

**核心技术函数接口 (Functions)**:
- `solver_status_record()`: Return a compact residual-aware solver status record.
- `solver_status_dataframe()`: Return solver status as a DataFrame.

---

### 文件模块: `solver_core\solve_path_integrator.py`
**技术描述**: Integrate V6.4 residual-loop diagnostics into solve-path certificates.

**核心技术函数接口 (Functions)**:
- `solve_recycle_flash_heat_loop()`: Return a combined solve-path status for recycle, flash and heat closure.
- `solve_path_integrator_dataframe()`: Return V6.4 solve-path integrator rows.
- `solve_path_integrator_gate()`: Return compact gate status for solve-path integration.

---

### 文件模块: `solver_core\stability_region.py`
**技术描述**: Dynamic stability-region summaries.

**核心技术函数接口 (Functions)**:
- `stability_region_record()`: Return a compact stability-region diagnostic.
- `stability_region_dataframe()`: Return dynamic stability-region rows.

---
