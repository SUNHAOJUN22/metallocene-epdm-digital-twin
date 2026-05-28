# metallocene-epdm-digital-twin

## 1. 项目定位

`metallocene-epdm-digital-twin` 是本地可运行的茂金属 EPM/EPDM 溶液聚合工艺仿真与研发级数字孪生平台。软件面向乙烯/丙烯/ENB 在烷烃/芳烃溶剂中的茂金属催化溶液聚合研发，用于趋势判断、实验设计、参数校准、牌号反推、工艺窗口筛选、热安全筛查、输送/挂胶风险识别、CFD可视化和报告归档。

本软件不是 Aspen Plus、Aspen Polymers、Fluent、OpenFOAM 或工业设计包的替代品。所有动力学、热力学、流变、CFD、3D装置和优化模型均为研发级工程模型，需要结合真实物性、反应量热、VLE/溶解度、流变、中试数据和真实设备几何校准。

## 2. 当前版本

当前版本：**V6.4 / 0.7.4**

V6.4 目标：在 V6.3 方程导向求解、数据同化、物性运行时和可信度证书基础上，升级为 **“真实方程导向求解闭环 + 工业实验数据同化 + 自适应 DAE 求解器 + 物性校准主流程深接入 + 模型可信度证书 UI 化”** 的研发级/工业验证级数字孪生平台。

## 3. 版本更新记录

### V6.5 half-hour quality sprint

V6.5 本轮为 30 分钟质量增强冲刺，基于 V6.4 / 0.7.4 代码和 release-gate 契约执行，不做强制版本号升级。冲刺目标是发现 P0/P1/P2 风险、验证数理/单位/守恒/趋势门禁、刷新 QA 文档，并记录下一轮 P3 优先级。

V6.5 冲刺结果：

- `python -m pytest -q tests`: 344 passed。
- `python scripts\auto_functional_audit.py`: 150/150 passed。
- `python scripts\function_inventory_audit.py`: 254/254 modules imported，971/971 public callables directly referenced。
- `python scripts\performance_profile.py`: passed。
- `python scripts\ui_e2e_smoke.py` 与 `python scripts\ui_e2e_workflow.py`: HTTP 200，15 pages registered，18 manual actions mapped，export actions not heavy。
- `python scripts\dev_tasks.py quality-gate`: passed。
- 第二轮复测：`python scripts\release_gate.py` passed，`Invoke-WebRequest http://127.0.0.1:8501/` 返回 HTTP 200。
- 2026-05-20 V6.5+ 复测：遍历 1217 个项目文件后，`pytest` 344 passed、`auto_functional_audit` 150/150 passed、`function_inventory_audit` 971/971、`quality-gate` passed、`release_gate` passed、Streamlit HTTP 200。
- 2026-05-20 可用性增强：新增 UI action registry usability gate，检查 action id 唯一、必填字段、用户反馈、导出输出声明、重复 action signature 和同页重复标签；复测 `pytest` 346 passed、`auto_functional_audit` 151/151 passed、`function_inventory_audit` 972/972、`release_gate` passed。
- 2026-05-20 质量冲刺复跑：`check-env`、`pytest`、`auto_functional_audit`、`function_inventory_audit`、`performance_profile`、`ui_e2e_smoke`、`ui_e2e_workflow`、`quality-gate`、`generate-test-report`、`continuous-improve`、`release_gate` 和 Streamlit HTTP 检查全部通过。
- 2026-05-20 数理严谨性复跑：新增 `docs/V6_5_MATH_RIGOR_AUDIT.md`，复核单位/量纲、finite/nonnegative/bounded、守恒残差、方程/benchmark/lineage、thermo/flash/transport/rheology/heat、dynamic ODE/DAE、residual-aware optimizer/DOE/posterior、report/repro/UI gates；`pytest` 346 passed，`auto_functional_audit` 151/151 passed，`function_inventory_audit` 972/972，`release_gate` passed，Streamlit HTTP 200。
- 2026-05-20 市场 skill 工作流替换：新增 `docs/MARKET_SKILL_REPLACEMENT_PLAN.md`，将 UI inspection、Excel QA、Word report QA、GitHub PR/CI、OpenAI API/Agents lookup、slide generation 和 bitmap visual workflows 映射到当前可用市场 skill；运行时数理内核仍保留在项目代码中，由 pytest/audit/release gate 守护。
- 2026-05-20 专业 skill 实际接管验收：新增 `docs/MARKET_SKILL_ACTUAL_REPLACEMENT_AUDIT.md`；`browser` 已实际打开并检查 Streamlit，`spreadsheets` 已实际导入并检查 `smoke.xlsx`，`documents` 已实际渲染 `smoke.docx`。数理/物理运行时内核不替换，继续由可执行测试和 release gate 守护。
- 2026-05-20 市场 skill 安装增强：通过 OpenAI skills 仓库安装 `playwright`、`playwright-interactive`、`screenshot`、`pdf`、`security-best-practices`、`security-threat-model`、`jupyter-notebook`、`chatgpt-apps`，用于后续 UI 自动化、PDF QA、安全审计、威胁建模、校准 notebook 和 ChatGPT Apps 集成；这些不替代运行时数理内核。
- 2026-05-20 市场 skill 严格补装：新增 `security-ownership-map` 和 `sentry`；前者需要 git 历史用于安全所有权/Bus factor 分析，后者需要 Sentry CLI/auth 用于生产错误观测。二者不参与物理模型有效性判定。
- 2026-05-20 14:38 数理严谨性 + 专业 skill QA 复跑：`pytest` 346 passed、`auto_functional_audit` 151/151 passed、`function_inventory_audit` 972/972、`quality-gate` passed、`release_gate` passed、Streamlit HTTP 200；`browser`、`spreadsheets`、`documents` 再次接管 UI/Excel/Word 外围 QA，未发现 P0/P1/P2。
- 2026-05-20 14:59 数理严谨性 + 专业 skill QA 再次复跑：`pytest` 346 passed、`auto_functional_audit` 151/151 passed、`function_inventory_audit` 972/972、`quality-gate` passed、`release_gate` passed、Streamlit HTTP 200；Excel 173 sheets 且 0 个公式错误，Word 报告 12 页渲染成功。
- 2026-05-20 15:36 稳定性遍历：修正包级 `epdm_sim.__version__` 旧元数据，使其与正式 V6.4 / 0.7.4 发布契约一致；未改变任何数理模型、残差阈值、benchmark 或 report/repro 行为；复测 `pytest` 346 passed、`auto_functional_audit` 151/151、`function_inventory_audit` 972/972、`quality-gate` passed、`release_gate` passed、Streamlit HTTP 200。
- 2026-05-20 15:59 稳定性与数理逻辑遍历复核：重新遍历 1222 个核心文件，确认 `epdm_sim.__version__`、`pyproject.toml`、registry 和 report/repro 版本契约一致；复测 `pytest` 346 passed、`auto_functional_audit` 151/151、`function_inventory_audit` 972/972、`quality-gate` passed，未发现 P0/P1/P2。
- `docs/V6_5_CHANGELOG.md` 和 `docs/V6_5_HALF_HOUR_AUDIT.md` 已记录冲刺事实。

V6.5 结论：

- 未发现 P0/P1/P2 问题。
- 未修改模型公式、求解器或测试标准。
- 剩余风险为 P3：大文件拆分、真实工业数据接入、synthetic/regression benchmark 替换、nonlinear residual loop 更深接入真实 recycle/flash/heat-balance solve path。

### V6.4 / 0.7.4 nonlinear residual loop, industrial data and governance UI

#### V6.4 vs V6.3

V6.4 不重写现有主模型，而是把 V6.3 的 equation-oriented solver certificate 推进为可审计的非线性 residual iteration 和 solve-path integrator。新增 nonlinear residual loop、solve path integrator、industrial data package、benchmark reconciliation、property runtime audit、adaptive integrator、event localization、residual decision engine 和 model governance page，使守恒残差、工业证据、校准物性、动态事件和模型可信度进入同一个可追踪闭环。

V6.4 新增/修改内容：

- 新增 `solver_core/nonlinear_residual_loop.py` 与 `solver_core/solve_path_integrator.py`，记录 residual norm、bounded projection、Jacobian condition、accepted/rejected 和 suspected source。
- 新增 `industrial_data_package.py` 与 `benchmark_reconciliation.py`，对 plant/experiment/literature/synthetic/regression benchmark 做 schema、unit、uncertainty、validity 和 confidence 审计。
- 新增 `property_runtime_audit.py`，验证 calibrated Henry、viscosity、flash-K correction 与 deltaH 的 runtime 使用不破坏 residual safety。
- 新增 `dynamic_core/adaptive_integrator.py` 与 `dynamic_core/event_localization.py`，把 residual acceptance、state invariant、stiffness 和 event risk 汇总为 adaptive integration/event localization 证据。
- 新增 `residual_aware_decision_engine.py`，统一 optimizer/DOE/posterior/uncertainty 候选点的 residual、validity、uncertainty 和 rejected_reason 审计。
- 新增 `governance_certificate.py` 与 `pages/model_governance_page.py`，在 UI 诊断路径展示 confidence score、equation/residual/benchmark/data-lineage traceability、property selection、fallback 和 release-gate status，页面切换不触发重任务。
- Excel 报告新增 `nonlinear_residual_loop`、`solve_path_integrator`、`industrial_data_package`、`benchmark_reconciliation`、`property_runtime_audit`、`adaptive_integrator`、`event_localization`、`residual_decision_engine`、`governance_certificate` 和 `V6_4_audit_summary`。
- repro package 新增 nonlinear residual iteration、solve path integrator、industrial data lineage、benchmark reconciliation、property runtime audit、adaptive integrator、event localization、residual decision engine 和 governance certificate snapshots。
- `auto_functional_audit.py` 和 `release_gate.py` 升级到 V6.4，新增 nonlinear_residual_loop、solve_path_integrator、industrial_data_package、benchmark_reconciliation、property_runtime_audit、adaptive_integrator、event_localization、residual_decision_engine、governance_certificate、Excel sheet-name compatibility、markdown changelog 和 public callable 100% gates。

V6.4 新增测试：

- `tests/test_nonlinear_residual_loop.py`
- `tests/test_solve_path_integrator.py`
- `tests/test_industrial_data_package.py`
- `tests/test_benchmark_reconciliation.py`
- `tests/test_property_runtime_audit.py`
- `tests/test_dynamic_adaptive_integrator.py`
- `tests/test_dynamic_event_localization.py`
- `tests/test_residual_aware_decision_engine.py`
- `tests/test_model_governance_page.py`

V6.4 最新验证结果：

- Targeted V6.4 core tests: 10 passed。
- `python -m pytest -q`: 344 passed。
- `python scripts\auto_functional_audit.py`: 150/150 passed。
- `python scripts\function_inventory_audit.py`: 254/254 modules imported，971/971 public callables directly referenced。
- `python scripts\dev_tasks.py quality-gate`: py_compile、pytest、smoke_app、auto_functional_audit、function_inventory_audit、performance_profile、ui_e2e_smoke、ui_e2e_workflow、static_contracts 全部 passed。
- `python scripts\release_gate.py`: all gates passed。
- `python scripts\performance_profile.py`: run_flowsheet、template flowsheet、dynamic explicit、small CFD、report export、cache key generation 全部 passed。
- `python scripts\ui_e2e_smoke.py` 与 `python scripts\ui_e2e_workflow.py`: 15 pages registered，18 manual actions 均有 TaskService mapping，export actions 未触发 heavy tasks。
- `Invoke-WebRequest http://127.0.0.1:8501/`: HTTP 200。

V6.4 已知局限性：

- nonlinear residual loop 仍是 bounded iteration/integration layer，后续需要继续扩大到更完整的 recycle/flash/heat-balance nonlinear solve replacement。
- industrial data package 仍基于本地 JSON/CSV metadata，尚未直接连接 LIMS/ELN/plant historian。
- adaptive integrator 已记录 rejected step/event localization 证据，但仍不是完整生产级 DAE event-location solver。

V6.5 下一步建议：

1. 将 nonlinear residual loop 更深接入 recycle、flash 和 heat-balance 的真实迭代路径。
2. 引入 LIMS/ELN/plant historian 数据接入和数据资产版本治理。
3. 将 adaptive integrator 推进为更完整的 DAE step rejection、event localization 和 algebraic constraint projection。
4. 扩展 model governance UI 的交互筛选、证据链 drill-down 和导出审计。

### V6.3 / 0.7.3 equation-oriented solving, data assimilation and confidence certificates

#### V6.3 vs V6.2

V6.3 把 V6.2 的 conservation solve path、property runtime、dynamic solver policy、residual-aware optimizer/DOE 和 evidence-chain score 进一步推进为可审计的方程导向闭环。新增 equation-oriented conservation solver 与 conservation Jacobian，用 bounded least-squares/Newton-style step 处理小 residual，并继续拒绝 polymer vapor、heat-duty 单位/符号错误和大 residual。新增 calibration data package 与 data assimilation，要求实验/工厂/文献数据具备 source_reference、uncertainty、validity_range 和 data_hash。新增 property runtime context，记录 calibrated property runtime 对主流程物性路径的影响及 residual 安全状态。新增 adaptive step control 和 dynamic event detection，将 residual、state invariant、stiffness 和 event risk 纳入动态求解诊断。新增 residual-aware sampling 和 model confidence certificate，用于 posterior/DOE/optimizer 候选点与工业证据链可信度审计。

V6.3 新增/修改内容：

- 新增 `solver_core/equation_oriented_solver.py` 和 `solver_core/conservation_jacobian.py`。
- 新增 `calibration_data_package.py` 和 `data_assimilation.py`。
- 新增 `property_runtime_context.py`。
- 新增 `dynamic_core/adaptive_step_control.py` 和 `dynamic_core/event_detection.py`。
- 新增 `residual_aware_sampling.py`。
- 新增 `model_confidence_certificate.py`。
- Excel 报告新增 `equation_oriented_solver`、`conservation_jacobian`、`calibration_data_package`、`data_assimilation`、`property_runtime_context`、`adaptive_step_control`、`dynamic_event_detection`、`residual_aware_sampling`、`confidence_certificate`、`validation_upgrade_plan` 和 `V6_3_audit_summary`。
- repro package 新增 equation-oriented solver certificate、conservation Jacobian、calibration package lineage、data assimilation、property runtime context、adaptive step control、dynamic event detection、residual-aware sampling、confidence certificate 和 validation upgrade plan snapshots。
- `auto_functional_audit.py` 和 `release_gate.py` 升级到 V6.3，新增 equation_oriented_solver、conservation_jacobian、data_assimilation、property_runtime_context、adaptive_step_control、dynamic_event_detection、residual_aware_sampling、confidence_certificate 和 V6.3 report/repro gates。

V6.3 新增测试：

- `tests/test_v6_3_math_core.py`

V6.3 最新验证结果：

- `python -m pytest -q`: 334 passed。
- `python scripts\dev_tasks.py quality-gate`: py_compile、pytest、smoke_app、auto_functional_audit、function_inventory_audit、performance_profile、ui_e2e_smoke、ui_e2e_workflow、static_contracts 全部 passed。
- `python scripts\auto_functional_audit.py`: 141/141 passed。
- `python scripts\function_inventory_audit.py`: 244/244 modules imported，935/935 public callables directly referenced。
- `python scripts\release_gate.py`: all gates passed。
- `python scripts\performance_profile.py`: run_flowsheet、template flowsheet、dynamic explicit、small CFD、report export、cache key generation 全部 passed。
- `python scripts\ui_e2e_smoke.py` 与 `python scripts\ui_e2e_workflow.py`: HTTP 200，14 pages registered，manual actions 均有 TaskService mapping，export actions 未触发 heavy tasks。
- `Invoke-WebRequest http://127.0.0.1:8501/`: HTTP 200。

V6.3 已知局限性：

- equation-oriented solver 仍是 bounded residual solve/certificate layer，尚未完全替代 flowsheet/recycle/flash/heat-balance 的全部非线性求解循环。
- data assimilation 当前使用本地 benchmark/calibration package metadata，尚未连接 LIMS、ELN 或 plant historian。
- adaptive step control 已提供 rejected-step/fallback 证据，但还不是完整 adaptive DAE integrator。

V6.4 下一步建议：

1. 将 equation-oriented residual solve 进一步接入 recycle/flash/heat-balance 的真实迭代循环。
2. 引入 plant historian / LIMS / ELN 数据 ingestion，并将 calibration package 变为可版本化数据资产。
3. 将 adaptive step control 扩展为真实 time-step rejection、event localization 和 DAE constraint projection。
4. 将 confidence certificate 暴露到 UI model-governance dashboard。

### V6.2 / 0.7.2 conservation solve path, runtime property models and evidence-chain scoring

#### V6.2 vs V6.1

V6.2 不重写现有主模型，而是把 V6.1 的证书、bridge 和决策层进一步接入可审计运行路径：新增 conservation solve path，把小质量/能量/flash/recycle residual 的闭合、拒绝和 certificate 作为显式求解证据；新增 property model runtime，使 calibrated Henry、viscosity、flash-K correction 和 deltaH 在 validity range 内能真实影响 solubility、rheology、flash 和 heat-release 结果；新增 dynamic solver policy 与 step acceptance，让 stiffness、state invariant、residual acceptance、event risk 和 quench/cooling failure 共同影响 fallback 决策；新增 residual-aware optimizer/DOE，把 residual critical 和 outside validity 候选点直接拒绝；新增 evidence chain score，把 equation、residual、benchmark、data lineage、source reference 和 confidence level 汇总为可审计可信度评分。

V6.2 新增/修改内容：

- 新增 `solver_core/conservation_solve_path.py`：`apply_conservation_corrections_to_flowsheet()`、`solve_flash_with_mass_closure()`、`solve_heat_balance_with_energy_closure()`、`solve_recycle_with_residual_acceptance()` 和 `conservation_solve_certificate_dataframe()`。
- 新增 `property_model_runtime.py`：在明确启用且处于 validity range 内时，calibrated Henry、viscosity、flash-K correction 和 deltaH 影响主流程相关计算，默认仍保持 `default_estimate`。
- 新增 `dynamic_core/solver_policy.py` 和 `dynamic_core/step_acceptance.py`：输出 solver policy reason、step acceptance table、residual acceptance rate 和 fallback 诊断。
- 新增 `residual_aware_optimizer.py` 和 `residual_aware_doe.py`：optimizer/DOE 目标加入 residual penalty、validity penalty、benchmark failure 和 lineage confidence。
- 新增 `evidence_chain_score.py`：输出 evidence-chain score、critical gate 和 evidence gap priority，包含 VLE/flash recovery、reaction calorimetry、solution rheology、GPC/Mooney、dynamic T/P profile 和 plant mass-balance reconciliation 数据缺口。
- Excel 报告新增 `conservation_solve_path`、`conservation_solve_cert`、`property_model_runtime`、`dynamic_solver_policy`、`dynamic_step_acceptance`、`residual_aware_optimizer`、`evidence_chain_score`、`evidence_gap_priority` 和 `V6_2_audit_summary`。
- repro package 新增 `conservation_solve_certificate.csv`、`property_model_runtime.csv`、`dynamic_solver_policy.csv`、`dynamic_step_acceptance.csv`、`residual_aware_optimizer.csv`、`residual_aware_doe.csv`、`evidence_chain_score.csv` 和 `evidence_gap_priority.csv`。
- `auto_functional_audit.py` 和 `release_gate.py` 升级到 V6.2，新增 conservation solve path、property model runtime、dynamic solver policy、dynamic step acceptance、residual-aware optimizer/DOE、evidence-chain score、Excel sheet-name compatibility、markdown changelog 和 public callable 100% gates。

V6.2 新增测试：

- `tests/test_v6_2_math_core.py`

V6.2 最新验证结果：

- Targeted V6.2 core tests: `tests/test_v6_2_math_core.py` 已通过。
- Report/repro compatibility tests: `tests/test_report_consistency.py`、`tests/test_repro_package.py`、`tests/test_audit_trail.py` 已通过。
- 全量 `quality-gate`、`release_gate`、UI smoke/workflow 和 Streamlit HTTP 复测结果见 `docs/TEST_REPORT.md` 与 `docs/QUALITY_BASELINE.md`。

V6.2 已知局限性：

- conservation solve path 仍是 bounded correction/acceptance layer，不替代完整 flowsheet nonlinear equation-oriented solver。
- calibrated property runtime 需要更多 plant/experiment/literature 数据才能达到工业设计精度；当前优先保证趋势、单位、validity 和 lineage 可审计。
- dynamic solver policy 已进入 fallback/step-acceptance 诊断，但仍不是完整 DAE event-location 和 adaptive integration framework。
- evidence chain score 依赖本地 JSON/CSV metadata，LIMS/ELN/historian 接入留待后续版本。

V6.3 下一步建议：

1. 将 conservation solve path 接入更多 recycle/flash/heat-balance 迭代循环，并输出 equation-oriented residual Jacobian 诊断。
2. 引入真实 plant historian / LIMS / ELN 数据包，补齐 VLE、量热、流变、GPC/Mooney、flash recovery 和 dynamic T/P profile 高置信 benchmark。
3. 将 dynamic solver policy 推进到 adaptive time-step rejection、event localization 和 DAE algebraic constraint projection。
4. 将 property model runtime 的校准选择接入 UI 参数集管理和 model confidence dashboard。

### V6.1 / 0.7.1 math-core correction, decision and evidence-chain governance

#### V6.1 vs V6.0

V6.1 不重写主模型，而是把 V6.0 的证书型治理推进到更具体的决策层：新增 conservation correction certificate，明确小 residual 可闭合、大 residual 必须 critical；新增 calibrated property bridge，让校准 Henry/viscosity/flash-K/deltaH 在显式启用且处于 validity range 内时影响计算路径；新增 dynamic solver decision，将 stiffness、residual acceptance、state invariant 和 event risk 合并为 RK45/BDF/explicit fallback 决策；新增 residual-aware decision，统一 posterior、uncertainty 和 DOE 的 residual 风险评分；新增 evidence_chain，把 equation、residual、benchmark、data lineage 和 source reference 连成工业证据链。

V6.1 新增/修改内容：

- 新增 `solver_core/conservation_correction.py`：`close_small_mass_residual()`、`close_small_energy_residual()`、`close_flash_split_residual()` 和 `correction_certificate_dataframe()`。
- 新增 `property_model_bridge.py`：在 validity range 内应用 calibrated property model，超出范围时 fallback 到 default estimate 并输出 warning。
- 新增 `dynamic_core/solver_decision.py`：`choose_dynamic_solver()`、`dynamic_fallback_policy()`、`residual_based_step_acceptance()` 和 `dynamic_solver_decision_dataframe()`。
- 新增 `residual_aware_decision.py`：posterior/uncertainty/DOE 使用 residual risk、lineage confidence 和 candidate context 评分。
- 新增 `evidence_chain.py`：输出 evidence chain、evidence gaps、evidence-weighted confidence 和 evidence upgrade recommendations。
- 继续 API 兼容拆分：新增 `estimation/residual_objectives.py`、`fit_runner.py`、`fit_diagnostics.py`、`physical_penalties.py`，`reactor_core/reaction_balance.py`、`polymer_moments.py`、`heat_release.py`、`reactor_residuals.py`，`flowsheet_core/material_closure.py`、`energy_closure.py`、`unit_residuals.py`、`kpi_projection.py`，`dynamic_core/invariant_projection.py`、`event_certificates.py`，`fluid_core/property_selector_bridge.py`、`transport_residuals.py`。
- Excel 报告新增 `conservation_correction`、`correction_certificates`、`property_model_bridge`、`dynamic_solver_decision`、`residual_aware_decision`、`evidence_chain`、`evidence_gaps`、`V6_1_audit_summary`。
- repro package 新增 `correction_certificates.csv`、`property_model_bridge.csv`、`dynamic_solver_decision.csv`、`residual_aware_decision.csv`、`evidence_chain.csv`、`evidence_gaps.csv`。
- `auto_functional_audit.py` 和 `release_gate.py` 升级到 V6.1，新增 conservation correction、property bridge、dynamic solver decision、residual-aware decision、evidence chain、Excel sheet-name compatibility 和 markdown changelog gates。

V6.1 新增测试：

- `tests/test_v6_1_math_core.py`

V6.1 已知局限性：

- conservation correction 仍是小 residual 闭合和证书层，不替代完整非线性流程求解器。
- calibrated property bridge 需要更多真实 VLE、量热、流变和 flash recovery 数据，才能从治理路径升级为工业设计精度。
- dynamic solver decision 是 residual-aware fallback policy，不是完整 index-1 DAE 求解器。
- evidence chain 仍依赖本地 JSON/CSV metadata，LIMS/ELN/historian 接入留待后续版本。

V6.2 下一步建议：

1. 将 conservation correction 接入 recycle/flash/heat_balance 的求解循环，而不只是报告/门禁证书。
2. 为 plant/experiment/literature benchmark 引入 reviewed raw data package 和人工审核状态。
3. 将 property bridge 的 calibrated Henry/viscosity/deltaH 参数传入 solubility、rheology、flash 和 heat balance 的核心 correlation 调用。
4. 把 dynamic solver decision 推进到 adaptive time-step rejection 和 event handler 策略。

### V6.0 / 0.7.0 industrial math-core governance and traceability

#### V6.0 vs V5.7

V6.0 把 V5.7 的 equation-residual coupling、residual acceptance、benchmark source registry 和 calibrated property usage 推进到 **工业级数理内核 1.0**。新增 equation graph、residual graph 和 data-lineage graph，要求 critical equation 能追踪到 implementation、residual、benchmark、validity、fallback 和 data lineage。新增 constrained solver certificate、DAE/state invariant diagnostics、evidence-weighted model confidence、property model selector 和 industrial report/repro audit sheets。所有新增能力保持旧 API 兼容，不主动重跑 ODE/CFD/optimizer/posterior/DOE。

V6.0 新增/修改内容：

- 新增 `model_graph.py`、`residual_graph.py`、`data_lineage_graph.py`，输出 equation/residual/data-lineage traceability graph。
- 新增 `math_core/balance_laws.py`、`thermodynamic_identities.py`、`kinetic_identities.py`、`dimension_signatures.py`、`equation_graph.py`、`residual_graph.py`、`model_confidence.py`。
- 新增 `solver_core/constrained_solver.py`、`residual_minimizer.py`、`solver_certificates.py`、`dae_solver.py`、`stability_region.py`。
- 新增 `dynamic_core/dae_constraints.py` 和 `dynamic_core/state_invariants.py`，对 dynamic profile 做 DAE-style algebraic constraints、nonnegative states、T/P positivity、polymer/segment monotonic checks。
- 新增 `validation_evidence.py` 和 `model_confidence_engine.py`，将 plant/experiment/literature/synthetic/regression_snapshot evidence、ResidualSystem、equation binding、unit safety 和 validity envelope 合成为 evidence-weighted confidence。
- 新增 `property_model_selector.py`，按 parameter_type、validity range、source_type、confidence score 选择 calibrated/default property model。
- Excel 报告新增 `model_traceability_graph`、`equation_graph`、`residual_graph`、`data_lineage_graph`、`solver_certificates`、`dae_constraints`、`state_invariants`、`validation_evidence`、`model_confidence`、`confidence_decomposition`、`property_model_selection`、`residual_aware_calibration`、`residual_aware_posterior`、`residual_aware_doe`。
- repro package 新增 traceability graph、solver certificate、validation evidence、confidence decomposition 和 property model selection snapshots。
- `release_gate.py` 升级到 V6.0，新增 markdown changelog gate，并检查 README/model_registry/equation_registry/golden benchmark 版本一致性。

V6.0 新增测试：

- `tests/test_v6_0_industrial_math_core.py`

V6.0 已知局限性：

- V6.0 的 constrained solver 是 residual-aware certificate/correction layer，尚未替代所有旧优化器内部的非线性求解路径。
- DAE/state invariant 目前以 profile 后验和 fallback decision support 为主，未引入完整 index-1 DAE 求解器。
- plant/experiment benchmark 仍依赖本地 JSON metadata，真实 LIMS/ELN/historian 接入留待 V6.1。
- property model selector 已可选择 calibrated/default model，但主流程核心 correlations 仍需要更多实测 VLE、量热、流变和 flash recovery 数据校准。

V6.1 下一步建议：

1. 将 constrained solver certificate 的 residual norm 和 constraint violations 直接并入 optimizer / DOE / posterior 的每次目标函数评价。
2. 引入真实 plant/experiment benchmark ingestion，并为 source_reference、review_status、uncertainty 建立人工审核流程。
3. 把 property model selector 接入 solubility、flash、rheology、heat_balance 的运行参数分发层。
4. 将 DAE/state invariant 从报告型 gate 推进到 dynamic solver step rejection / adaptive fallback policy。

### V5.7 / 0.6.7 equation-residual coupling, residual acceptance and benchmark source registry

#### V5.7 vs V5.6

V5.7 把 V5.6 的 data lineage、residual constrained fit、posterior residual filter 和 equation reverse check 进一步整合为 **方程-残差-实验数据三闭环**。新增 `math_core/` 和 `solver_core/` 分层 helper，在不破坏旧 API 的前提下，把 equation binding、ResidualSystem acceptance、物理约束、bounded solver step、residual projection 和 fallback policy 放入独立内核层。新增 `equation_residual_coupling.py`，要求 critical equation 同时具备 implementation、benchmark、residual_id、dimensional signature 和 trend/reverse checks。新增 `residual_acceptance.py`，统一 calibration、optimizer、DOE、posterior、uncertainty 的 residual acceptance 表。新增 `dynamic_core/stability_checks.py`，用 finite/nonnegative/monotonic/residual-feedback 检查构成 proof-style dynamic stability gate。新增 `benchmark_source_registry.py` 和 `data/benchmark_sources.json`，把 benchmark source、source_reference、uncertainty、validity range、review status 和 release eligibility 显式化。`calibrated_property_models.py` 新增 calibrated property usage selector，支持 Henry、viscosity、flash-K 和 deltaH 的可选校准模型路径。

V5.7 新增/修改内容：

- 新增 `math_core/`：`equations.py`、`residuals.py`、`constraints.py`、`acceptance.py`、`diagnostics.py`。
- 新增 `solver_core/`：`bounded_solver.py`、`residual_projection.py`、`fallback_policy.py`、`solver_status.py`。
- 新增 `equation_residual_coupling.py`，实现 equation-code-residual-benchmark 三向一致性 gate。
- 新增 `residual_acceptance.py`，统一 calibrated set、optimizer、DOE、posterior 的 residual acceptance policy。
- 新增 `dynamic_core/stability_checks.py`，检查 dynamic profile 的 finite、nonnegative、monotonic、residual feedback 和 stiffness indicator。
- 新增 `benchmark_source_registry.py` 和 `data/benchmark_sources.json`，区分 plant / experiment / literature / synthetic / regression_snapshot 置信等级和 release eligibility。
- `calibrated_property_models.py` 新增 `select_calibrated_property_model()`、`apply_calibrated_property_value()` 和 `calibrated_property_usage_dataframe()`。
- Excel 报告新增 `equation_residual_coupling`、`residual_acceptance`、`dynamic_stability_checks`、`benchmark_sources`、`benchmark_lineage`、`calibrated_property_usage`、`calibration_lineage`。
- repro package 新增 `benchmark_sources.csv`、`benchmark_lineage.csv`、`equation_residual_coupling.csv`、`residual_acceptance.csv`、`calibrated_property_usage.csv`。
- `auto_functional_audit.py` 和 `release_gate.py` 升级到 V5.7，新增 equation-residual coupling、residual acceptance、dynamic stability checks、benchmark source registry、calibrated property usage 和 report/repro audit consistency gates。

V5.7 新增测试：

- `tests/test_v5_7_math_kernel.py`

V5.7 已知局限性：

- `math_core/` 和 `solver_core/` 目前是 API-compatible governance/helper layer，尚未完全替换 `parameter_estimation.py`、`reactor.py`、`flowsheet.py`、`dynamic_template_reactor.py` 等旧入口。
- `benchmark_sources.json` 仍以本地 metadata 为主，未直接连接 LIMS、ELN 或 plant historian。
- calibrated property usage selector 已提供主流程可选路径，但真实 Henry/VLE/流变/量热参数仍需要实验数据持续补齐。

V5.8 下一步建议：

1. 将 `math_core.acceptance` 和 `solver_core.fallback_policy` 进一步接入 optimizer / DOE / posterior 的真实执行路径。
2. 将 calibrated property usage 接入 solubility、flash、rheology 和 heat_balance 的运行参数分发层。
3. 为 dynamic ODE 增加 step-level residual feedback 对 BDF/RK fallback 的真实 solver decision。
4. 接入真实 plant/experiment 数据源，替换 synthetic/regression snapshot benchmark 的 release 权重。

### V5.6 / 0.6.6 data lineage, residual-constrained fitting and reverse equation checks

#### V5.6 vs V5.5

V5.6 继续把 V5.5 的 residual solver、benchmark calibration 和 RHS-residual coupling 推进到校准可信度闭环：benchmark 现在带有 data lineage；参数估计目标显式包含 data residual、守恒/相平衡/能量 residual penalty、prior penalty 和 extrapolation penalty；posterior samples 会经过 residual acceptance filter；equation registry 增加从代码输出反查 registry 单位、趋势、benchmark 和 residual link 的 reverse check；dynamic residual 进入 solver diagnostics / fallback decision；calibrated property models 记录 dataset_id、data_hash、validity_range、uncertainty 和 source_type。

V5.6 新增/修改内容：

- 新增 `data_lineage.py`，为 benchmark / calibration dataset 生成 `dataset_id`、`source_type`、`source_reference`、`measurement_unit`、`uncertainty`、`validity_range`、`data_hash` 和 lineage confidence。
- 新增 `estimation/residual_constrained_fit.py`，将参数估计目标写成 `weighted_data_residual + mass/energy/phase residual penalty + prior penalty + extrapolation penalty`，并拒绝 unit mismatch 或 critical residual 的 calibrated set。
- 新增 `posterior_residual_filter.py`，对 posterior samples 执行 parameter bounds + ResidualSystem acceptance，输出 `residual_acceptance_rate`。
- 新增 `equation_reverse_check.py`，从 implementation 输出反查 equation registry 的 `input_units`、`output_unit`、`dimensional_signature`、`benchmark_id` 和 `residual_id` 完整性。
- 新增 `dynamic_core/residual_feedback.py`，把 dynamic residual severity 写入 solver status，暴露 `residual_max_error`、`residual_acceptance_rate`、`fallback_reason`、`nfev/njev/step_count`。
- 新增 `calibrated_property_models.py`，为 Henry/viscosity/flash-K/deltaH 等校准模型记录 dataset lineage、uncertainty、validity range 和 confidence score。
- Excel 报告新增 `data_lineage`、`residual_constrained_fit`、`posterior_residual_filter`、`equation_reverse_check`、`dynamic_residual_feedback`、`calibrated_property_models`。
- repro package 新增 `data_lineage.csv`、`calibrated_property_models.csv`、`equation_reverse_check.csv`。
- `auto_functional_audit.py` 和 `release_gate.py` 升级到 V5.6，新增 data lineage、residual constrained fit、posterior residual filter、equation reverse check、dynamic residual feedback、calibrated property model 和 report/repro lineage consistency gates。

V5.6 新增测试：

- `tests/test_v5_6_math_kernel.py`

V5.6 最新验证结果：

```text
auto_functional_audit: 106/106 passed
function_inventory_audit: 172/172 modules imported; 734/734 public callables directly referenced
targeted regression: tests/test_v5_6_math_kernel.py and V5.5/V5.4 report/repro tests passed
```

V5.6 已知局限性：

- data lineage 目前以本地 JSON/CSV metadata 为主，尚未连接 LIMS、plant historian 或 ELN。
- residual-constrained fit 是 deterministic acceptance/objective helper，还不是完整非线性约束优化器。
- calibrated property models 支持保存/加载和 audit scoring，但仍需要真实 VLE、量热、流变、flash recovery 和 GPC/Mooney 数据持续扩展。

V5.7 下一步建议：

1. 将 residual-constrained fit 接入实际 least_squares / differential_evolution 参数估计路径，保留 critical residual rejection。
2. 为 plant/experiment benchmark 增加原始数据导入、版本化预处理和 reviewer 审核状态。
3. 将 dynamic residual feedback 用于 BDF/RK fallback 自动判据，并增加更严格的 step-level accumulation residual。
4. 将 calibrated property models 与 Henry、flash-K correction、rheology 和 heat balance 的运行参数集连接。

### V5.5 / 0.6.5 residual-solver, RHS coupling and benchmark calibration

#### V5.5 vs V5.4

V5.5 继续把 V5.4 的残差、单位和 benchmark 框架向数理内核内部推进：ResidualSystem 不只作为报告项，还提供 residual solver、correction trace 和优化/DOE/posterior 约束接口；动态 ODE 不只输出 profile，还提供 RHS term 与 residual time-series 的绑定表；benchmark 不只做 metadata gate，还开始给出 weighted residual、confidence adjustment 和 calibration data gaps。

V5.5 新增/修改内容：

- 新增 `residual_solver.py`，提供 `residual_weighted_objective()`、`solve_recycle_with_residual_minimization()`、`adjust_flash_split_to_close_mass()`、`heat_balance_residual_correction()`、`residual_acceptance_summary()` 和 correction trace。小误差可审计闭合，大误差会标记 error/critical。
- 新增 `dynamic_core/rhs_terms.py` 和 `dynamic_core/residual_timeseries.py`，把 RHS term 的 `affected_state`、`unit`、`physical_meaning`、`source_equation_id` 和 `residual_id` 显式输出，用于动态 ODE residual coupling gate。
- 新增 `benchmark_calibration.py`，对 synthetic / literature / experiment / plant / regression_snapshot benchmark 做置信加权，输出 benchmark residual、model-confidence adjustment 和下一批数据缺口建议。
- 将大模块按数理职责拆出薄 helper 包：`estimation/`、`reactor_core/`、`flowsheet_core/`、`dynamic_core/`、`fluid_core/`。旧 API 保持兼容，拆分包只复用已有模型，不替代已验证主流程。
- Excel 报告新增 `residual_solver`、`residual_correction_trace`、`rhs_term_diagnostics`、`benchmark_calibration`、`benchmark_data_gaps`、`posterior_residual_acceptance`、`uncertainty_residual_risk`、`dynamic_residual_timeseries`。
- repro package 新增 `benchmark_residuals.csv`、`benchmark_data_gaps.csv`、`unit_conversion_trace.csv`、`residual_correction_trace.csv`。
- `auto_functional_audit.py` 和 `release_gate.py` 升级到 V5.5，新增 residual_solver、RHS-residual coupling、benchmark calibration、posterior residual acceptance、report/repro audit consistency gates。

V5.5 新增测试：

- `tests/test_v5_5_math_kernel.py`

V5.5 质量门禁新增：

```text
residual_solver gate:
  residual correction 只能做小范围数值闭合，critical residual 直接阻断优化/DOE/后验推荐

RHS-residual coupling gate:
  dynamic ODE profile 必须能追溯到 RHS term、source equation 和 residual id

benchmark calibration gate:
  benchmark 按 source_type 和 confidence_level 加权，失败会降低可信度并输出数据缺口

report/repro audit gate:
  报告与复现实验包必须包含 residual solver、benchmark calibration、unit trace 和 metadata snapshot
```

V5.5 已知局限性：

- 新增拆分包目前以 API-compatible helper 为主，`parameter_estimation.py`、`reactor.py`、`flowsheet.py` 等大文件仍保留旧入口；V5.6 应继续把内部实现迁移到拆分包。
- residual solver 目前是 bounded correction / rejection 机制，不是完整非线性方程组求解器。
- experimental benchmark 已进入 calibration scoring，但真实 plant/experiment 数据仍需持续补充。

V5.6 下一步建议：

1. 将 `parameter_estimation.py` 的目标函数、约束和置信区间完全迁移到 `epdm_sim/estimation/`。
2. 将 reactor material balance 和 rate engine 进一步迁移到 `reactor_core/`，减少 EPDM adapter 与通用模板内核耦合。
3. 为 residual solver 增加小规模 nonlinear least-squares closure mode，但必须保留 correction threshold 和 suspected_source。
4. 用真实 VLE、量热、流变、GPC/Mooney、中试动态 T/P/Q 数据替换更多 synthetic benchmark。

### V5.4 / 0.6.4 residual-aware mathematical kernel and experimental benchmark gates

#### V5.4 vs V5.3

V5.4 把 V5.3 已建立的量纲、残差、方程绑定和 benchmark 框架继续向“可执行求解约束”推进：单位入口不再只是工具函数，ResidualSystem 不再只是报告行，benchmark 不再只是回归快照，而是进入 release gate、DOE/优化过滤、模型审计和复现实验包。

V5.4 新增/修改内容：

- 新增 `residual_objective.py`，提供 `residual_objective_score()`、`reject_if_critical_residual()`、`residual_penalty_for_optimizer()`、`residual_filter_for_doe()` 和 `residual_diagnostics_dataframe()`；optimizer/DOE/window 对 critical residual 执行强过滤或 penalty。
- 新增 `dynamic_residuals.py`，对动态 ODE profile 计算 finiteness、polymer mass monotonic、quench reaction residual、heat generation、pressure positivity 等时间序列残差。
- 新增 `phase_equilibrium_constraints.py`，把 PR/SRK root classification、fugacity positivity、K-value ordering、flash component split/polymer vapor/RR residual 变成可执行门禁。
- 新增 `experimental_benchmark.py` 和 `data/experimental_benchmarks.json`，为 synthetic/literature/plant/regression_snapshot benchmark 增加 source_type、confidence_level、validity_range、equation/residual linkage 和 hash 检查。
- `flash.py`、`heat_balance.py`、`rheology.py`、`fluid_props.py` 进一步接入 `DimensionedValue` unit-safe adapters，支持 MPa/Pa、°C/K、kJ/h/kW、cP/Pa.s 等等价输入，同时拒绝错误量纲。
- `constrained_window.py`、`bayesian_doe.py`、`optimizer.py` 使用 residual objective 或 residual acceptance 过滤不守恒候选点。
- Excel 报告新增 `unit_conversion_trace`、`residual_objective`、`dynamic_residuals`、`phase_equilibrium_constraints`、`experimental_benchmarks`、`residual_aware_optimization`、`residual_aware_doe`。
- repro package 新增 `experimental_benchmarks.json`，并同步 manifest 到 `V5.4 / 0.6.4`。
- `auto_functional_audit.py` 和 `release_gate.py` 升级到 V5.4，新增 unit-safe entry、unit conversion trace、residual objective、dynamic residual、phase-equilibrium constraints、experimental benchmark、residual-aware DOE gates。

V5.4 新增测试：

- `tests/test_v5_4_math_core.py`

V5.4 质量门禁新增：

```text
unit-safe entry gate:
  flash/heat/rheology/ODE 接收带单位输入和旧 float 输入，错误单位不得进入模型计算

residual objective gate:
  critical residual 产生强 penalty，DOE/optimizer/window 不推荐 residual critical 点

dynamic residual gate:
  动态 profile 必须 finite，聚合物质量非下降，quench 后 rate 接近 0，压力保持正值

phase-equilibrium constraints gate:
  EOS roots、fugacity、K-value ordering、flash residual 和 polymer nonvolatile 约束必须通过

experimental benchmark gate:
  benchmark metadata hash、source/confidence、validity 和 equation/residual linkage 必须可审计
```

V5.4 已知局限性：

- `experimental_benchmarks.json` 已提供实验/文献/plant-style 元数据接口，但多数仍是 synthetic 或 placeholder benchmark；真实 VLE、量热、流变、GPC/Mooney 数据仍需导入。
- residual objective 已进入 optimizer/DOE/window，但还不是严格 NLP/DAE residual solve；V5.5 应把 residual penalty 接入更多求解迭代和参数后验。
- 相平衡约束仍基于研发级 Wilson/PR/SRK 近似，不替代工业 VLE 回归包。
- 动态残差目前从 profile 后验计算，V5.5 应进一步把 accumulation residual 与 RHS solver step 绑定。

V5.5 下一步建议：

1. 用真实实验数据替换更多 regression_snapshot benchmark，并给 tolerance 建立来源。
2. 把 residual objective 进一步接入 parameter estimation/posterior 的采样接受准则。
3. 为 dynamic ODE 增加 step-level mass/energy accumulation residual 和 sparse Jacobian 一致性测试。
4. 将 phase-equilibrium constraints 扩展到多压力、多温度、多溶剂 benchmark。

### V5.3 / 0.6.3 equation-driven physical constraints and full-chain dimensional gates

#### V5.3 vs V5.2

V5.3 把 V5.2 的量纲、残差、方程绑定和 benchmark 框架继续推进到模型约束、报告、DOE/优化过滤和复现实验包中。核心变化是：残差不再只是报告表，方程注册表不再只是文档，单位适配不再只是工具函数。

V5.3 新增/修改内容：

- `dimensioned.py` 增加 `ensure_temperature_K`、`ensure_pressure_Pa`、`ensure_mass_flow_kg_h`、`ensure_molar_flow_mol_h`、`ensure_concentration_mol_L`、`ensure_power_kW`、`ensure_viscosity_Pa_s`、`ensure_density_kg_m3`、`ensure_length_m`、`ensure_time_min`，核心入口可接收 `DimensionedValue`、`(value, unit)` 或旧 float。
- `template_ode_rhs.py` 在动态 ODE context 和初始状态中接入温度、压力、时间 unit adapter，避免 K/°C、MPa/Pa 静默混用。
- `residual_system.py` 增加 `critical` severity、`critical_residuals()` 和 `residual_system_acceptance()`；critical residual 会阻断 DOE/工艺窗口推荐。
- `model_audit_report.py` 将 residual system score 写入校准/可信度摘要；残差不达标会降低 numerical score 并生成风险提示。
- `bayesian_doe.py` 和 `constrained_window.py` 增加 residual_system feasibility 过滤，不推荐 critical residual 失败的实验点或工艺窗口。
- `equation_binding.py` 为关键方程增加 `residual_id`，并要求 implementation、benchmark、dimensional signature 和 residual linkage 可验证。
- `ode_diagnostics.py` 增加 `RHSTermDiagnostic` 和 `rhs_terms_diagnostics_dataframe()`，报告 RHS 分项的 value、unit、affected_state、physical_meaning、finite_check。
- `thermo_consistency.py` 增加 `thermo_physical_constraints_dataframe()`；`transport_core.py` 增加 `transport_physical_constraints_dataframe()`。
- `scientific_benchmarks.py` 和 `data/golden_benchmarks.json` 升级到 V5.3 benchmark schema，增加 `residual_id`、`expected_output` 和 V5.3 benchmark version。
- Excel 报告新增 `dimensioned_inputs`、`residual_system_detailed`、`rhs_diagnostics`、`thermo_physical_constraints`、`transport_physical_constraints`、`fallback_diagnostics`。
- repro package 新增 `residual_system.csv` 和 `benchmark_snapshot.json`，并同步 manifest 到 `V5.3 / 0.6.3`。
- release gate 升级为 V5.3，检查 README、model registry、equation registry、benchmark version、V5.3 roadmap 文档和 100% direct callable reference。

V5.3 新增测试：

- `tests/test_v5_3_math_kernel.py`

V5.3 质量门禁新增：

```text
dimensioned input gate:
  temperature/pressure/viscosity adapters reject incompatible units and produce base units

residual critical gate:
  critical residual count must be zero for default flowsheet and recommended candidates

equation binding completeness gate:
  critical equations must have implementation, benchmark, dimensional signature and residual id

RHS diagnostics gate:
  RHS physical terms must be finite and unit-labeled

thermo/transport physical constraints gates:
  EOS, Henry, flash, viscosity, pressure-drop and heat-transfer trends must pass

benchmark acceptance gate:
  golden benchmark versions must start with V5.3 and benchmark checks must pass
```

V5.3 已知局限性：

- `DimensionedValue` 已接入核心入口适配，但并未完全替代所有内部裸 float；V5.4 应继续推进到 flash、heat balance、transport 和 optimizer 的每个内部中间量。
- ResidualSystem 已用于 audit、DOE 和窗口过滤，但单元操作级 residual 诊断仍是工程近似，真实工业闭合仍需要实测 purge/recycle/flash 组成数据。
- 热力学、流变和动力学 benchmark 仍包含研发回归快照；V5.4 应使用真实 VLE、量热、流变、GPC/Mooney 数据替代更多快照 benchmark。
- BDF 已有 state scaling 和 fallback 诊断，但解析/稀疏 Jacobian 仍是下一轮重点。

V5.4 下一步建议：

1. 将 `DimensionedValue` 作为 `TemplateProcessConfig` 的可选内部表示，减少所有模型入口的单位假设。
2. 将 `ResidualSystem` 拆成 reactor/flash/recycle/heat/product/dynamic 分层诊断并在 UI 显示。
3. 为 BDF stiff solver 增加 sparse Jacobian pattern 和事件一致性测试。
4. 用真实实验数据更新 benchmark 的 `source_or_reason` 和 tolerance。

### V5.2 / 0.6.2 math-core residual, dimensional and equation-binding hardening

#### V5.2 vs V5.1

V5.2 把 V5.1 已有的发布级测试体系继续向数理内核推进，重点不在新增页面，而在让核心方程、单位、守恒残差、ODE诊断、热力学/输运检查和 benchmark acceptance 可机器验证。

V5.2 新增/修改内容：

- 新增 `epdm_sim/dimensioned.py`：轻量 `DimensionedValue` 量纲安全层，覆盖温度、压力、质量/摩尔流量、浓度、功率、黏度、密度、长度和时间；禁止 K/°C、Pa/MPa、mol/L/mol/m3 等静默混用。
- 新增 `epdm_sim/residual_system.py`：把质量、组分、相分配、反应生成、热释放和动态积累从“后验描述”升级为统一 `ResidualSystem`，报告 `lhs/rhs/absolute_error/relative_error/suspected_source/suggested_fix`。
- 新增 `epdm_sim/equation_binding.py`：将 equation registry 的关键公式绑定到真实实现函数，检查 implementation 可导入、趋势测试可运行、benchmark_id 和量纲签名存在。
- 新增 `epdm_sim/ode_diagnostics.py`：为动态模板反应器 RHS 提供 feed、reaction、gas-liquid transfer、pressure control、heat generation/removal、catalyst decay、quench 等项级诊断。
- 新增 `epdm_sim/transport_core.py`：把流变、压降和传热核心趋势统一成可测试 gate，覆盖 `solids ↑ -> viscosity ↑`、`T ↑ -> viscosity ↓`、`D ↓ -> ΔP ↑`、`UA ↑ -> cooling capacity ↑`。
- 新增 `epdm_sim/parameter_constraints.py`：为动力学、传递、流变和热力学参数记录 bounds、unit、prior 和 physical meaning，非法参数不进入拟合/后验/不确定性链路。
- `reporting/excel.py` 增加 `residual_system`、`equation_binding`、`equation_binding_checks`、`dimensional_signature`、`ode_diagnostics`、`thermo_math_core`、`transport_core`、`parameter_constraints`、`extrapolation_risk`、`benchmark_acceptance` sheets。
- `auto_functional_audit.py` 增加 residual system、equation binding、dimensional signature、ODE diagnostics、transport core、parameter constraints gates。
- `scientific_benchmarks.py` 和 `data/golden_benchmarks.json` 增加 residual system score benchmark，并要求 benchmark 版本为 `V5.2 / 0.6.2`。
- `repro_package.py`、`model_registry.json`、`equation_registry.json`、`pyproject.toml` 同步到 `V5.2 / 0.6.2`。

V5.2 新增测试：

- `tests/test_dimensioned.py`
- `tests/test_residual_system.py`
- `tests/test_equation_binding.py`
- `tests/test_ode_diagnostics.py`
- `tests/test_transport_core.py`
- `tests/test_parameter_constraints.py`

V5.2 新增质量门禁：

```text
residual_system gate:
  default flowsheet residual score >= 70 and critical residuals cannot be error

equation_binding gate:
  every critical equation has implementation_function, benchmark_id and dimensional_signature

dimensional_signature gate:
  critical equation trend smoke tests pass and units are explicit

ODE diagnostics gate:
  RHS diagnostic terms are finite and no error severity is emitted

transport_core gate:
  viscosity, pressure-drop and cooling-capacity trend checks pass

benchmark acceptance gate:
  golden_benchmarks model_version starts with V5.2
```

V5.2 已知局限性：

- `DimensionedValue` 是轻量单位层，不是完整符号量纲代数系统；复杂组合量仍依赖 equation binding 和 dimensional checks。
- `ResidualSystem` 当前以 flowsheet/dynamic profile 可用字段构造核心残差，工业级原子衡算、真实设备热损和多相传质仍需实验数据和设备几何校准。
- BDF 求解仍保留 explicit fallback；V5.3 建议继续推进刚性ODE的解析/稀疏Jacobian和状态尺度归一化。
- 热力学和流变仍是研发筛选模型；V5.3 应优先接入真实 VLE、溶解度、量热、流变和中试数据进行参数再校准。

V5.3 下一步建议：

1. 把 `DimensionedValue` 更深入接入 `template_ode_rhs`、`flash`、`heat_balance` 和 `transport_core` 的核心计算入口。
2. 为 BDF stiff solver 增加稀疏 Jacobian pattern、事件一致性测试和动态积累残差分解。
3. 用真实 VLE/流变/量热数据更新 golden benchmark 来源和容差。
4. 将 residual system 失败定位接入 UI 性能诊断和 model audit 风险排序。

### V5.1 / 0.6.1 coverage, benchmark, validity and report consistency

#### V5.1 vs V5.0

V5.1 相比 V5.0 的更新：

- 新增 `epdm_sim/validity_envelope.py`：从 `model_registry`、`reaction_templates` 和物性来源读取适用范围，对温度、压力、停留时间、rpm、管径、流量、单体进料等输入给出 `inside / near_edge / outside / unknown` 分类。
- 新增 `epdm_sim/report_consistency.py`：检查 Excel 报告、复现实验包 manifest、导出 metadata、未运行重任务清单和 required sheets 的一致性。
- 新增 `scripts/performance_profile.py`：输出 `tmp_smoke_outputs/performance_profile.json/csv`，覆盖 `run_flowsheet`、`run_template_flowsheet`、动态 explicit、small CFD、Excel报告导出和 cache key。
- `scientific_benchmarks.py` 和 `data/golden_benchmarks.json` 升级为 V5.2 benchmark schema：每个 benchmark 记录 input、expected、unit、tolerance、model_version、equation_id、validity_range、source_or_reason。
- 新增函数级真实调用测试，将 public callable direct reference 从 V5.0 的 397/570 提升到 V5.2 的至少 450 门槛；当前目标模块包括 `fluid_props`、`flowsheet`、`parameter_estimation`、`recipe`、`dimensional_checks`、`bayesian_doe`、`constrained_window`、`digital_twin_3d`、`posterior`、`reactor`、`rheology`、`sensitivity`。
- 物性/热力学校准结果增加 dataset_id、created_at、data_hash、MAE、RMSE、R2、validity_range 和持久化函数，不覆盖 default 参数。
- `model_audit_report.py` 增加 kinetic/property/thermo/validation calibration score proxy。
- `report.py` 新增 Excel sheets：`validity_envelope`、`performance_profile`、`report_consistency`、`calibration_scores`。
- `scripts/release_gate.py` 升级为 V5.2 gate：增加 performance profile、direct reference >= 450、benchmark version、V5.2 audit 文档、README/model_registry/equation_registry 版本一致性检查。
- `data/model_registry.json` 更新到 `0.6.2`，`data/equation_registry.json` 更新到 `V5.2`，`pyproject.toml` 更新到 `0.6.2`。
- 新增审计文档：`docs/V5_1_FULL_AUDIT.md`。

V5.2 新增/修改模块：

- 新增：`validity_envelope.py`、`report_consistency.py`、`scripts/performance_profile.py`、`tests/test_v5_1_direct_coverage.py`、`tests/test_validity_envelope.py`、`tests/test_calibration_persistence.py`、`tests/test_model_audit_calibration_scores.py`、`tests/test_performance_profile_contract.py`、`tests/test_report_consistency.py`、`docs/V5_1_FULL_AUDIT.md`
- 修改：`scientific_benchmarks.py`、`property_calibration.py`、`thermo_calibration.py`、`model_audit_report.py`、`report.py`、`repro_package.py`、`scripts/release_gate.py`、`scripts/auto_functional_audit.py`、`data/golden_benchmarks.json`、`data/model_registry.json`、`data/equation_registry.json`、README
- 废弃：无。

V5.2 关键公式和质量门禁：

```text
Validity envelope:
  status = inside       if low <= x <= high and not near boundary
  status = near_edge    if x is within 10% of range edge
  status = outside      if x < low or x > high
  validity_score = 100 - 25*N_outside - 7.5*N_near_edge - 5*N_unknown

Calibration metrics:
  residual_i = observed_i - predicted_i
  MAE = mean(|residual_i|)
  RMSE = sqrt(mean(residual_i^2))
  R2 = 1 - sum((observed-predicted)^2) / sum((observed-mean(observed))^2)

Performance profile:
  runtime_s = perf_counter_after - perf_counter_before
  profile tasks are deterministic smoke cases and do not replace scale benchmarks.

Report consistency:
  required_sheets must exist
  export_metadata must include software version, config hash, parameter set id,
  template id, model registry hash and equation registry hash
  report export must not trigger ODE/CFD/optimization/posterior/DOE/uncertainty
```

V5.2 自动测试和质量门禁命令：

```powershell
python scripts\dev_tasks.py check-env
python scripts\dev_tasks.py audit-project
python scripts\dev_tasks.py quality-gate
python scripts\dev_tasks.py generate-test-report
python scripts\dev_tasks.py continuous-improve
python scripts\performance_profile.py
python scripts\release_gate.py
```

V5.2 当前验证结果记录：

```text
V5.2 新增定向测试：validity envelope、calibration persistence、model audit calibration scores、performance profile、report consistency、direct coverage、scientific benchmarks
release_gate 门槛：direct reference >= 450，performance_profile 输出存在，V5.2 docs/registry/README/benchmark 版本一致
```

V5.2 已知局限性：

- validity envelope 使用注册表和模板中的研发级范围，不代表严格工业设计边界。
- performance profile 是小案例 smoke，不是严格统计性能基准；不同工作站波动未设置硬 runtime 阈值。
- 报告一致性检查覆盖 metadata 和 required sheets，但 Word/PDF 版式仍依赖人工或后续 artifact 渲染验证。
- 校准持久化已经记录数据集和误差指标，但真实可信度仍取决于本地实验数据质量。

V5.2 建议：

- 将 `report.py` 拆入 `epdm_sim/reporting/`，保持旧 import 兼容。
- 将 `parameter_estimation.py` 拆入 `epdm_sim/estimation/`。
- 将 performance profile 的 smoke 结果升级为多次重复运行和分位数阈值。
- 将 validity envelope 扩展到 DOE/optimizer 候选过滤的强约束。
- 建立可选 Playwright 全链路 UI，但继续禁止页面切换触发重任务。

### V5.0 / 0.6.0 stiff ODE, property calibration and validation campaign

#### V5.0 vs V4.9

V5.0 相比 V4.9 的更新：

- 新增 `epdm_sim/ode_jacobian.py`，提供有限差分 Jacobian 与 scaled Jacobian 工具；`dynamic_template_reactor.py` 的 `solve_ivp_bdf` 现在先通过 `ode_scaling.bdf_readiness_check()` 判定状态尺度是否适合 BDF。通过时调用 SciPy BDF + scaled finite-difference Jacobian；不通过或求解失败时返回 `explicit_bounded` 工程化 fallback，并在 `summary` 中记录 `solver_status`、`nfev`、`njev`、`step_count`、`fallback_reason`。
- `ode_scaling.py` 的 BDF readiness 门禁更严格：当状态尺度跨度过大时自动建议 fallback，防止发布门禁被刚性求解器卡住。当前默认 EPDM 配置因压力与催化剂活性尺度跨度大，会采用受控 fallback；这不是无条件跳过，而是可审计的工程判定。
- 新增 `epdm_sim/property_calibration.py`，支持流变黏度参数和表观聚合热 `deltaH` 的研发级拟合，输出 `fitted_params`、`confidence_interval`、`residuals`、`validity_range` 和 warning。
- 新增 `epdm_sim/thermo_calibration.py`，支持 Henry 溶解度参数与 flash K 修正因子的校准，保留默认参数不覆盖，输出残差、置信区间代理和温压适用范围。
- 新增 `data/validation_datasets.json` 与 `epdm_sim/validation_campaign.py`，建立“实验数据 -> 模型运行 -> 残差/偏差 -> 可信度 -> 下一批验证数据建议”的工程验证数据闭环。
- `model_audit_report.py` 扩展 property calibration metrics，可将物性/热力学校准质量纳入模型审计。
- `report.py` 增加 `all_plot_validation`、`validation_campaign`、`validation_model_bias`、`validation_next_data` 等 Excel sheets；报告导出仍不主动运行 ODE/CFD/优化/后验/DOE 等重模型。
- 新增 `scripts/ui_e2e_workflow.py`，做非破坏性 UI 工作流 contract smoke：检查 HTTP/页面注册/Workflow Wizard/UI action/task service 映射，不点击重计算按钮。
- `scripts/release_gate.py` 升级为 V5.0 gate：增加 `ui_e2e_workflow`、V5.0 文档存在性、README/model_registry/equation_registry 版本一致性、function inventory artifact 检查。
- `data/model_registry.json` 更新到 `0.6.0`，`data/equation_registry.json` 更新到 `V5.0`，`golden_benchmarks.json` 的模型版本同步为 V5.0。
- 新增/扩展直接覆盖测试：`test_bdf_stiff_solver.py`、`test_property_calibration.py`、`test_thermo_calibration.py`、`test_validation_campaign.py`、`test_fluid_props_more_direct.py`、`test_conservation_diagnostics_direct.py`、`test_thermo_direct.py`、`test_cfd_fields_direct.py`、`test_ui_e2e_workflow_contract.py`。
- 新增审计文档：`docs/V5_0_FULL_AUDIT.md`。

V5.0 新增/修改模块：

- 新增：`ode_jacobian.py`、`property_calibration.py`、`thermo_calibration.py`、`validation_campaign.py`、`scripts/ui_e2e_workflow.py`、`data/validation_datasets.json`、`docs/V5_0_FULL_AUDIT.md`
- 修改：`dynamic_template_reactor.py`、`ode_scaling.py`、`model_audit_report.py`、`report.py`、`repro_package.py`、`scientific_benchmarks.py`、`scripts/release_gate.py`、`scripts/auto_functional_audit.py`、`data/model_registry.json`、`data/equation_registry.json`、`data/golden_benchmarks.json`、README 和相关测试
- 废弃：无。EPDM/Vistalon 仍为 application adapter；generic template 路径继续保留。

V5.0 关键公式和数理门禁：

```text
BDF state scaling:
  y_scaled_i = y_i / scale_i
  dy_scaled_i/dt = (dy_i/dt) / scale_i
  scale_i > 0 and finite
  if max(scale_i)/min(scale_i) > 1e8 -> fallback_recommended

Finite-difference Jacobian:
  J_ij ~= [f_i(y + h_j e_j) - f_i(y - h_j e_j)] / (2 h_j)
  h_j = max(abs_step, rel_step * max(|y_j|, 1))
  NaN/inf derivative columns are forced to finite fallback values.

Viscosity calibration:
  ln(mu / mu_solvent_T) = A_mu * solids + B_mu * solids^2 + alpha_Mw * ln(Mw/300000)
  solids is fraction, mu in Pa.s, T in K, Mw in g/mol

Heat release calibration:
  Q_rxn_kJ = |deltaH_kJ_mol| * consumed_mol
  exothermic chemistry convention stores deltaH_kJ_mol < 0

Henry calibration:
  C*_i = H_i(T, solvent) * P_i
  fitted solubility_ref_mol_L_MPa > 0
  validity_range tracks temperature_K and partial_pressure_MPa

Flash K correction:
  K_corrected = K_default * scalar_factor
  scalar_factor = median(observed_recovery / predicted_recovery), bounded positive

Validation campaign:
  bias_j = prediction_j - observation_j
  MAE_j = mean(|bias_j|)
  validation_score = bounded 0..100 proxy from endpoint residuals and warnings
```

V5.0 自动测试和质量门禁命令：

```powershell
$files = @('app.py') + (Get-ChildItem -Path epdm_sim,scripts -Recurse -Filter *.py | ForEach-Object { $_.FullName }); python -m py_compile @files
python -m pytest -q
python scripts\smoke_app.py
python scripts\auto_functional_audit.py
python scripts\function_inventory_audit.py
python scripts\ui_e2e_smoke.py
python scripts\ui_e2e_workflow.py
python scripts\release_gate.py
streamlit run app.py
```

V5.0 统一脚本入口：

```powershell
python scripts\dev_tasks.py check-env
python scripts\dev_tasks.py audit-project
python scripts\dev_tasks.py test-build
python scripts\dev_tasks.py test-unit
python scripts\dev_tasks.py test-integration
python scripts\dev_tasks.py test-e2e
python scripts\dev_tasks.py test-science
python scripts\dev_tasks.py test-units
python scripts\dev_tasks.py test-security
python scripts\dev_tasks.py quality-gate
python scripts\dev_tasks.py generate-test-report
python scripts\dev_tasks.py continuous-improve
```

等价 Makefile 入口：

```bash
make check-env
make audit
make test-build
make test-unit
make test-integration
make test-e2e
make test-science
make test-units
make test-security
make quality-gate
make report
make continuous-improve
```

V5.0 生成的持续验证文档：

- `docs/FUNCTION_MATRIX.md`
- `docs/TEST_REPORT.md`
- `docs/TESTING_STRATEGY.md`
- `docs/QUALITY_GATES.md`
- `docs/SCIENTIFIC_VALIDATION.md`
- `docs/UNIT_SYSTEM.md`
- `docs/KNOWN_LIMITATIONS.md`
- `docs/CHANGELOG_TESTING.md`
- `docs/QUALITY_BASELINE.md`
- `docs/OPTIMIZATION_ROADMAP.md`
- `docs/CONTINUOUS_IMPROVEMENT_LOG.md`

CI/CD 模板：

- `.github/workflows/ci.yml`
- `.github/workflows/quality-gate.yml`
- `.github/workflows/scientific-validation.yml`

V5.0 当前验证结果记录：

```text
最近复验：2026-05-08 14:27 Asia/Shanghai
py_compile：passed
新增 V5.0 定向测试：21 passed
python -m pytest -q：234 passed
python scripts\smoke_app.py：passed，smoke ok 15.548725734530445
python scripts\auto_functional_audit.py：74/74 checks passed
python scripts\function_inventory_audit.py：121/121 modules imported；397/570 public callables directly referenced；function_matrix=570 rows
python scripts\ui_e2e_smoke.py：passed；若 8501 未运行则执行静态 contract fallback；pages_registered=14；heavy export/action contracts clean
python scripts\ui_e2e_workflow.py：passed；若 8501 未运行则执行静态 contract fallback；Workflow Wizard registered；manual_action_count=18；heavy_manual_without_task=[]
python scripts\release_gate.py：py_compile、pytest、smoke_app、auto_functional_audit、function_inventory_audit、ui_e2e_smoke、ui_e2e_workflow、static_contracts 全部 passed
HTTP check：http://127.0.0.1:8501/ -> 200
输出：tmp_smoke_outputs/release_gate_summary.json、release_gate_summary.csv、function_matrix.csv、quality_gate_summary.csv、ui_e2e_workflow.json 等均存在
```

V5.0 已知局限性：

- 默认 EPDM BDF 路径因状态尺度跨度较大采用 `explicit_bounded` 工程化 fallback；真实 BDF 路径已接入，但需要更多状态缩放、事件平滑和刚性 benchmark 才能作为默认生产路径。
- 物性/热力学校准工具为研发级最小二乘/统计代理，不替代严格 VLE/流变/量热数据库。
- `validation_campaign` 使用 endpoint 数据做快速偏差诊断，时间序列验证仍依赖已有 `time_series_data/profile_alignment` 模块扩展真实数据。
- 全图表质量门禁目前覆盖报告注册图和关键科学图，后续新增图必须显式注册，否则不能保证被 `all_plot_validation` 捕获。
- UI E2E workflow 为非破坏性 contract smoke，不点击 ODE/CFD/优化/后验/DOE 重任务。

V5.2 建议：

- 用真实溶解度、VLE、流变和反应量热数据填充 calibrated property parameter sets，并将它们接入 active parameter set 管理。
- 对 BDF RHS 做事件连续化、稀疏 Jacobian pattern 和 step budget 诊断，减少 fallback。
- 将 validation campaign 扩展到动态时间序列 T/P/Q/solids/viscosity 残差。
- 建立 Playwright 可选 E2E，覆盖完整研发工作流但保持重任务手动触发。
- 将 report figure registry 改为强制声明式注册，新增图未声明单位时 release gate 直接失败。

### V4.9 / 0.5.6 release quality gates and scientific regression

#### V4.9 vs V4.8

V4.9 相比 V4.8 的更新：

- 新增 `epdm_sim/scientific_benchmarks.py` 和 `data/golden_benchmarks.json`，建立带模型版本、单位、容差和标准输入的 golden benchmark，覆盖默认 EPDM flowsheet、generic template flowsheet、flash/Rachford-Rice、Henry、rheology、heat duty、dynamic reactor 和 CFD diagnostics。
- 新增 `tests/test_property_invariants.py`，用固定随机种子和显式断言验证核心物理不变量：conversion/vapor fraction/risk probability 有界，composition closure 接近 100 wt%，kg/h↔mol/h、C↔K、MPa↔Pa 单位往返一致，密度/Cp/导热系数/黏度为正。
- 新增 `epdm_sim/plot_validation.py` 和 `tests/test_plot_validation.py`，对 Plotly 图进行非空数据、坐标轴单位、色标/hover说明检查。Excel 报告新增 `plot_validation` sheet。
- 新增 `epdm_sim/file_security.py` 和 `tests/test_file_security.py`，提供安全文件名、路径穿越、扩展名、文件大小和导出元数据门禁。`report.py` 与 `repro_package.py` 已接入 `export_metadata`。
- 新增 `epdm_sim/ode_scaling.py` 和 `tests/test_ode_scaling.py`，显式管理 `solve_ivp_bdf` 技术债：状态量缩放往返、正有限尺度估计和 `bdf_readiness_check()`。当前 BDF 仍为受控 fallback，不声称工业级刚性求解完成。
- 新增 `scripts/ui_e2e_smoke.py` 和 `tests/test_ui_e2e_static_contract.py`，执行非破坏性 UI E2E smoke：HTTP入口、标题/关键文本、页面注册、UI action/task service 合同，不点击 ODE/CFD/后验/DOE/优化/报告等重任务。
- 新增 `scripts/release_gate.py` 和 `tests/test_release_gate_script.py`，统一执行 py_compile、pytest、smoke_app、auto_functional_audit、function_inventory_audit、ui_e2e_smoke 和静态版本/文档/CSV artifact 检查，输出 `release_gate_summary.json/csv`。
- 新增/扩展函数级直接覆盖测试：`test_fluid_props_direct.py`、`test_equipment_3d_direct.py`、`test_utils_direct.py`、`test_ui_theme_direct.py`、`test_kinetics_direct.py`、`test_solubility_direct.py`、`test_template_flowsheet_direct.py`、`test_plotting_units.py`、`test_service_cache_keys.py`、`test_simulation_service.py` 等，针对 V4.8 function inventory 中直接覆盖缺口最大的模块补测。
- `data/model_registry.json` 版本更新到 `0.5.6`，与 README 当前版本保持一致。
- 新增审计文档：`docs/V4_9_FULL_AUDIT.md`。
- 新增门禁报告：`docs/V4_9_RELEASE_GATE_REPORT.md`。

V4.9 新增/修改模块：

- 新增：`scientific_benchmarks.py`、`plot_validation.py`、`file_security.py`、`ode_scaling.py`、`scripts/ui_e2e_smoke.py`、`scripts/release_gate.py`、`data/golden_benchmarks.json`、`docs/V4_9_FULL_AUDIT.md`、`docs/V4_9_RELEASE_GATE_REPORT.md`
- 新增测试：`test_scientific_benchmarks.py`、`test_property_invariants.py`、`test_plot_validation.py`、`test_file_security.py`、`test_ode_scaling.py`、`test_ui_e2e_static_contract.py`、`test_release_gate_script.py` 以及多个直接覆盖测试
- 修改：`report.py`、`repro_package.py`、`data/model_registry.json`、相关测试和 README
- 废弃：无。EPDM/Vistalon 继续作为 application adapter，generic template 路径继续保留。

V4.9 核心公式、默认参数和质量门禁：

```text
Golden benchmark:
  abs(model_value - expected_value) <= tolerance
  每个 benchmark 必须含 benchmark_id、expected、unit、tolerance、model_version

Physical invariants:
  0 <= conversion <= 1 或 0 <= conversion_pct <= 100
  0 <= vapor_fraction <= 1
  0 <= risk_probability <= 1
  sum(segment_wt%) ~= 100
  rho > 0, Cp > 0, k > 0, mu > 0

Unit roundtrip:
  kg/h -> mol/h -> kg/h
  C -> K -> C
  MPa -> Pa -> MPa

Plot validation:
  figure.data 非空
  numeric x/y axis title 不为空
  conversion/composition axis/hover 包含 % 或 wt%
  temperature 包含 °C 或 K
  pressure 包含 Pa/kPa/MPa
  viscosity 包含 Pa.s 或 Pa·s
  heat duty 包含 kW

File security:
  拒绝 ../ 路径穿越和 base_dir 逃逸
  只允许声明扩展名
  size_bytes <= max_bytes
  export_metadata 包含 version、timestamp、config_hash、parameter_set_id、template_id、registry hashes、warnings、unrun_heavy_tasks

BDF readiness:
  scale_i > 0 且 finite
  unscale(scale(y)) ~= y
  readiness = ready | fallback_recommended
```

V4.9 自动测试和质量门禁命令：

```powershell
$files = @('app.py') + (Get-ChildItem -Path epdm_sim,scripts -Recurse -Filter *.py | ForEach-Object { $_.FullName }); python -m py_compile @files
python -m pytest -q
python scripts\smoke_app.py
python scripts\auto_functional_audit.py
python scripts\function_inventory_audit.py
python scripts\ui_e2e_smoke.py
python scripts\release_gate.py
streamlit run app.py
```

V4.9 最新验证结果记录：

```text
最近复验：2026-05-08 10:56 Asia/Shanghai
py_compile：passed
新增 V4.9 定向测试：19 passed
python -m pytest -q：212 passed
python scripts\smoke_app.py：passed，smoke ok 15.548725734530445
python scripts\auto_functional_audit.py：74/74 passed
python scripts\function_inventory_audit.py：117/117 modules imported；339/554 public callables directly referenced；function_matrix=554 rows
python scripts\ui_e2e_smoke.py：passed；HTTP status 200；pages_registered=14；heavy export/action contracts clean
python scripts\release_gate.py：py_compile、pytest、smoke_app、auto_functional_audit、function_inventory_audit、ui_e2e_smoke、static_contracts 全部 passed
HTTP check：http://127.0.0.1:8501/ -> 200
In-app browser smoke：title=Metallocene EPDM Digital Twin；温度/压力控件可见；console error/warning=0
输出：tmp_smoke_outputs/release_gate_summary.json、release_gate_summary.csv、function_matrix.csv、quality_gate_summary.csv 等均存在
```

V4.9 已知局限性：

- UI E2E 为非破坏性 smoke，不点击重计算按钮；真实 Playwright/Cypress 级多步工作流留到 V5.0。
- Golden benchmark 是回归稳定性基准，不是工业设计标准值；公式变更时必须显式更新 benchmark 版本。
- `solve_ivp_bdf` 仍被技术债门禁管理，当前 release path 允许 fallback，不代表刚性ODE工业求解完成。
- Plot unit validation 当前覆盖关键图表，不保证所有未来新增图表自动纳入，后续应在 report quality gate 中强制枚举所有生成图。
- 文件安全层覆盖本地路径和扩展名风险；不替代企业级上传隔离、病毒扫描或权限系统。

V5.0 建议：

- 引入可选 Playwright E2E，覆盖完整“模板选择 -> 快速流程 -> 检查 -> 参数估计 -> DOE -> 报告/复现包”工作流，但仍不自动触发重模型。
- 将 BDF stiff ODE 做状态标度化、事件根定位和刚性求解性能测试。
- 把 plot validation 纳入所有 report figures 的强制质量门禁。
- 增加覆盖率报告和 mutation-style science invariant 测试。
- 用真实流变、溶解度、量热和时间序列数据扩展 property confidence 与 scientific benchmark。

### V4.8 / 0.5.5 template-native kernel and real solve_ivp RHS

#### V4.8 vs V4.7

V4.8 相比 V4.7 的更新：

- `run_flowsheet()` 公共入口改为通过 `TemplateProcessConfig -> run_template_flowsheet() -> EPDM adapter` 执行；原 EPDM 计算实现保留为 `_run_epdm_flowsheet_impl()`，因此旧 UI、报告和测试仍得到 `FlowsheetResult`，但公共主路径已经进入模板流程。
- `TemplateFlowsheetResult` 新增 `legacy_flowsheet` 字段，用于 EPDM adapter 返回旧结构，同时保留 `template_kpis` 与 `application_kpis` 分层。
- 新增 `epdm_sim/template_ode_rhs.py`：实现模板原生动态反应器 RHS，支持 `liquid_moles`、`gas_moles`、`segment_masses`、`chain_transfer_moles`、`polymer_mass_kg`、`T_K`、`P_Pa` 和 `catalyst_active_mol` 的真实状态导数。
- `dynamic_template_reactor.py` 的 `solve_ivp_rk45` 不再只是能力探针；现在会调用真实 `template_ode_rhs()` 积分模板状态向量，失败时回退 `explicit_bounded`。`solve_ivp_bdf` 在当前 MVP 自动巡检路径中明确降级，避免刚性求解器卡顿。
- 新增 `tests/test_template_ode_rhs.py`，覆盖 RHS 有限性、状态投影、solve_ivp路径和 EPDM兼容列。
- `data/model_registry.json` 更新到 `0.5.5`，新增 `template_config`、`template_flowsheet`、`template_ode_rhs`、`equation_code_consistency` 等 active 模块条目，并补齐 required units、数学检查、化工检查和 UI 触发策略。
- `data/equation_registry.json` 更新到 `V4.8`，新增模板进料摩尔换算、模板 segment 质量、模板液相单体动态衡算、模板动态能量衡算等机器可读公式。
- `report.py` Excel 导出新增/确保包含 `application_kpis`、`template_ode_rhs`、`ode_solver_diagnostics`、`model_registry_snapshot`、`registry_summary` 等 sheet。缺少动态ODE结果时写 `not_run`，不主动运行重模型。
- `repro_package.py` manifest 版本更新为 `V4.8 / 0.5.5`。
- 新增并扩展 `scripts/auto_functional_audit.py`：一键巡检主流程、模板泛化、动态ODE、CFD、DOE、守恒、趋势规则、注册表、报告导出和复现实验包，输出 `tmp_smoke_outputs/auto_functional_audit.csv`。当前巡检覆盖非法输入preflight、CFD/optimizer preflight、flash diagnostics、thermo K/EOS/Henry/Rachford-Rice、thermal safety、scale-up、property confidence、rheology、Plotly/3D/CFD图表、OpenFOAM zip、uncertainty、posterior、calibration loop、parameter estimation、optimizer、Pareto、constrained windows、surrogate physics、model audit、Excel/Word/repro package 等 74 项检查。
- 新增 `scripts/function_inventory_audit.py`：导入所有 `epdm_sim` 与 `app` 模块，生成公开函数/类清单与工业级功能矩阵，输出 `tmp_smoke_outputs/function_inventory_modules.csv`、`tmp_smoke_outputs/function_inventory_callables.csv`、`tmp_smoke_outputs/function_inventory_module_coverage.csv`、`tmp_smoke_outputs/function_inventory_uncovered_top20.csv`、`tmp_smoke_outputs/function_matrix.csv` 和 `tmp_smoke_outputs/quality_gate_summary.csv`，用于追踪后续直接测试覆盖率、UI/API/DB/文件/科学计算风险标签和未覆盖优先级。
- 修复 `dynamic_template_reactor.py` 的 generic template 可用性：`simulate_template_semibatch_ode()` 现在可直接接收 `TemplateProcessConfig`，不会再把模板配置错误地按 EPDM `ProcessConfig` 解包；新增回归测试覆盖 generic template + `TemplateProcessConfig` 动态路径。
- 优化 `solve_ivp_bdf` 动态反应器入口：V4.8 MVP 中 BDF 模式会明确降级到 `explicit_bounded`，避免刚性求解器在自动巡检中长时间卡住；`solve_ivp_rk45` 仍保留真实 RHS 路径，BDF 降级写入 summary/warnings 并有回归测试。
- 新增审计文档：`docs/V4_8_FULL_AUDIT.md`。
- 新增发布前验证报告：`docs/V4_8_INDUSTRIAL_VALIDATION_REPORT.md`，汇总功能矩阵、质量门禁、科学计算审查、UI/文件流/性能/安全审查、已修复问题和剩余风险。

V4.8 新增/修改模块：

- 新增：`template_ode_rhs.py`、`tests/test_template_ode_rhs.py`、`tests/test_function_inventory_audit.py`、`scripts/auto_functional_audit.py`、`scripts/function_inventory_audit.py`、`docs/V4_8_FULL_AUDIT.md`
- 修改：`flowsheet.py`、`template_flowsheet.py`、`dynamic_template_reactor.py`、`tests/test_dynamic_template_reactor.py`、`report.py`、`repro_package.py`、`__init__.py`、`data/model_registry.json`、`data/equation_registry.json`、`scripts/auto_functional_audit.py`、`scripts/function_inventory_audit.py`、`README.md`
- 废弃：无。EPDM/Vistalon 功能继续作为 application adapter 保留。

V4.8 核心公式和默认参数：

```text
Template feed conversion:
  F_i_mol_h = feed_i_kg_h * 1000 / MW_i_g_mol
  feed_i >= 0, MW_i > 0

Template segment mass:
  M_segment_kg_h = sum(n_i_consumed_mol_h * MW_i_g_mol / 1000)
  consumed_i <= feed_i
  segment_wt_sum ~= 100 wt%

Template liquid monomer ODE:
  dN_i_liq/dt = F_i,in + kLa_i*(a_i*N_i_gas - b_i*N_i_liq) - r_i*V
  units: mol/min
  kLa proxy is a screening correlation, not a validated industrial transfer coefficient.

Template dynamic energy balance:
  dT/dt = (Q_rxn - Q_removed)/(M_holdup*Cp)
  Q_rxn = sum(r_i*V*abs(deltaH_i))
  Q_removed = max(UA*(T - T_coolant), 0)

solve_ivp modes:
  explicit_bounded: robust fallback
  solve_ivp_rk45: scipy RK45 using template_ode_rhs
  solve_ivp_bdf: explicit_bounded fallback in current MVP audit path; future stiff solver path requires scaling work

State protection:
  liquid/gas moles >= 0
  segment/polymer mass >= 0 and nondecreasing in profile
  T_K finite and bounded for diagnostics
  P_Pa positive
  quench time ~= 0.90 * total_time_min
```

V4.8 验收结果记录：

```text
最近复验：2026-05-08 10:34 Asia/Shanghai
$files = @('app.py') + (Get-ChildItem -Path epdm_sim,scripts -Recurse -Filter *.py | ForEach-Object { $_.FullName }); python -m py_compile @files
结果：passed
python -m pytest tests\test_dynamic_template_reactor.py tests\test_function_inventory_audit.py -q
结果：8 passed
python -m pytest -q
结果：193 passed
python scripts\smoke_app.py
结果：smoke ok 15.548725734530445
python scripts\auto_functional_audit.py
结果：74/74 checks passed
python scripts\function_inventory_audit.py
结果：113/113 modules imported；278/534 public callables directly referenced by tests or audit scripts；function_matrix=534 rows；输出未直接覆盖最多的前20个模块
streamlit run app.py --server.headless true --server.port 8501
结果：http://127.0.0.1:8501/ HTTP 200
浏览器 UI smoke：标题 Metallocene EPDM Digital Twin；关键输入控件和视图切换控件可见；console error/warning = 0
本轮结论：未发现崩溃、NaN/inf、负流量/负物性、守恒error、趋势规则失败、UI重任务误触发或报告导出误触发重模型。
```

完整验收仍应运行：

```text
python -m py_compile app.py epdm_sim/**/*.py scripts/**/*.py
python -m pytest
python scripts/smoke_app.py
python scripts/auto_functional_audit.py
python scripts/function_inventory_audit.py
streamlit run app.py
```

V4.8 已知局限性：

- generic template flowsheet 仍是表观筛选模型，需要实验数据校准后才能用于定量设计。
- solve_ivp RHS 的 kLa、UA、压力动态是研发级代理模型，不是工业反应器设计方程；`solve_ivp_bdf` 在当前MVP中为防止自动巡检卡顿，明确降级到 `explicit_bounded`，后续需要真实刚性ODE标度化和事件求解优化。
- 部分 UI 页面仍以 EPDM 快捷字段作为默认展示，需要 V4.9 继续把页面输入和图表切换为 template-first。
- sensitivity、DOE、uncertainty 和 constrained windows 已有模板能力，但默认候选空间仍偏 EPDM 应用。

V4.9 建议：

- 将 sensitivity、Bayesian DOE、uncertainty 和 constrained windows 的内部变量完全迁移到 template KPI schema；
- 页面输入由 reaction template 自动生成，并只在 EPDM 模板下显示 Vistalon 对标；
- 报告按 template/application 双层结构组织章节；
- 用实验 kLa、UA、流变和时间序列数据替换动态ODE代理参数。

### V4.7 / 0.5.4 template main flowsheet, posterior confidence and audit trail

#### V4.7 vs V4.6

V4.7 相比 V4.6 的更新：

- 新增 `epdm_sim/template_config.py`：引入 `TemplateProcessConfig`，用 `monomer_feeds_kg_h` 和 `chain_transfer_feeds` 作为通用进料结构，同时保留 EPDM 快捷字段映射。
- 新增 `epdm_sim/feed_adapter.py`：实现 `build_template_feed_stream()` 和 `validate_template_feed_map()`，generic monomer 即使不在 `components.json` 中，也可通过 reaction template 的 molecular weight 生成 molar feed。
- 新增 `epdm_sim/template_flowsheet.py`：建立 `TemplateFlowsheetResult`、`run_template_flowsheet()`、`run_epdm_flowsheet_adapter()`、`template_stream_table()`、`template_unit_table()` 和 `template_mass_balance()`。EPDM 默认路径委托既有 validated flowsheet，generic template 走轻量表观聚合路径并显式闭合 segment mass。
- `dynamic_template_reactor.py` 新增 `solver_mode="explicit_bounded" | "solve_ivp_rk45" | "solve_ivp_bdf"`、solve_ivp 能力探针、fallback 标记和事件日志。
- 新增 `epdm_sim/ode_events.py`：定义 `quench_event`、`runaway_event`、`feed_cutoff_event`、`end_reaction_event` 与事件表。
- 新增 `epdm_sim/equation_tests.py`：把 equation registry 的关键公式与实际代码进行趋势一致性验证，覆盖 Arrhenius、ENB压力因子、氢调Mw、反应热、Wilson K、Rachford-Rice、Henry、黏度、压降、Fox Tg 和牌号匹配。
- 新增 `epdm_sim/posterior.py`：实现轻量 bounded random-walk MCMC，输出 posterior samples、可信区间、参数相关性和 acceptance rate。
- 新增 `epdm_sim/constrained_window.py`：实现工程约束工艺窗口推荐，硬约束包括 `cooling_margin > 0`、`fouling_index < 3`、压降、固含和 ENB residue margin。
- 新增 `epdm_sim/audit_trail.py`：记录 action/task/input/output hash、参数集、模板、状态、耗时和错误；`repro_package.py` 将 `audit_trail.csv` 写入复现实验包。
- 新增 `epdm_sim/workflow_wizard.py` 和 `epdm_sim/pages/workflow_wizard_page.py`：提供“选择模板/案例 -> 快速流程 -> 检查 -> 数据导入 -> 参数估计/后验 -> 不确定性 -> DOE -> 窗口优化 -> ODE/CFD复核 -> 报告/复现包”的研发向导，不自动触发重任务。
- 新增 `epdm_sim/cfd/grid_convergence.py`：支持 template scalar labels 和 40x20/80x40 等网格诊断，输出 `max_T`、`dead_zone_fraction`、`wall_fouling_max`、`pressure_drop`、`mixing_index` 和 convergence score。
- `ui_workflow.py` 与 `TaskService` 注册 V4.7 新动作：`run_posterior_sampling`、`run_constrained_window`、`run_cfd_grid_convergence`。
- `report.py` Excel新增 `template_config`、`template_flowsheet`、`equation_code_checks`、`posterior_summary`、`posterior_samples`、`constrained_windows`、`audit_trail`、`workflow_wizard`、`cfd_grid_convergence` sheets；缺失重任务结果写 `not_run`，不主动重跑。
- 新增审计文档：`docs/V4_7_FULL_AUDIT.md`。

V4.7 新增/修改模块：

- 新增：`template_config.py`、`feed_adapter.py`、`template_flowsheet.py`、`ode_events.py`、`equation_tests.py`、`posterior.py`、`constrained_window.py`、`audit_trail.py`、`workflow_wizard.py`、`pages/workflow_wizard_page.py`、`cfd/grid_convergence.py`
- 修改：`dynamic_template_reactor.py`、`ui_workflow.py`、`services/task_service.py`、`repro_package.py`、`report.py`、`app.py`、`__init__.py`、`README.md`
- 新增测试：`test_template_config.py`、`test_feed_adapter.py`、`test_template_flowsheet.py`、`test_ode_events.py`、`test_equation_code_consistency.py`、`test_posterior.py`、`test_constrained_window.py`、`test_audit_trail.py`、`test_workflow_wizard.py`、`test_cfd_grid_convergence.py`
- 废弃：无。EPDM/Vistalon 功能仍作为 application adapter 保留。

V4.7 核心公式、默认参数和数理约束：

```text
TemplateProcessConfig:
  monomer_feeds_kg_h[monomer] >= 0
  chain_transfer_feeds[agent] >= 0
  EPDM aliases:
    ethylene_kg_h -> monomer_feeds_kg_h["ethylene"]
    propylene_kg_h -> monomer_feeds_kg_h["propylene"]
    enb_kg_h -> monomer_feeds_kg_h["ENB"]
    hydrogen_g_h -> chain_transfer_feeds["hydrogen"]

Template generic flowsheet:
  feed_moles_i = feed_kg_h_i * 1000 / MW_i
  conversion_i = bounded(residence_factor * catalyst_factor * pressure_penalty, 0, 0.85)
  consumed_i <= feed_moles_i
  segment_mass_j = sum(consumed_i * MW_i / 1000)
  polymer_mass = sum(segment_mass_j)
  segment_wt_j = 100 * segment_mass_j / polymer_mass
  total mass closure = product + vapor - feed

Dynamic template reactor solver modes:
  explicit_bounded: default robust bounded profile
  solve_ivp_rk45: scipy RK45 template RHS path with fallback
  solve_ivp_bdf: explicit_bounded fallback in current MVP audit path
  quench_event: catalyst_active -> 0
  runaway_event: T_K > high_alarm_K
  feed_cutoff_event: P_Pa >= pressure_setpoint
  end_reaction_event: t >= recipe_end

Equation-code consistency:
  Arrhenius: d k / d T >= 0
  ENB pressure factor: factor(2.0 MPa) <= factor(0.7 MPa)
  Hydrogen chain transfer: d Mw / d C_H2 <= 0
  Q_rxn: d Q / d consumed_mol >= 0
  Wilson K: K_i finite and positive
  Rachford-Rice: vapor_fraction in [0,1]
  Henry Cstar: d Cstar / d P >= 0
  Solution viscosity: d mu / d solids >= 0, d mu / d T <= 0
  Darcy-Weisbach: smaller D -> larger DeltaP
  Fox Tg: finite Tg
  Grade score: closer product -> higher match score

Posterior sampling:
  bounded random-walk Metropolis
  parameters bounded by PARAMETER_BOUNDS
  acceptance_rate in [0,1]
  failed model/proxy run -> finite penalty, no crash

Constrained window hard constraints:
  cooling_margin_kW > 0
  fouling_index < 3
  pipe_pressure_drop_kPa < 1000
  solids_wt < 35
  ENB_residue_ppm < 50000
```

V4.7 默认关键参数：

| 参数/对象 | 默认值 | 单位 | 所在模块 | 说明 |
|---|---:|---|---|---|
| `TemplateProcessConfig.template_id` | EPDM_EPM_metallocene_solution | - | `template_config.py` | 默认反应模板 |
| `TemplateProcessConfig.monomer_feeds_kg_h` | EPDM alias map | kg/h | `template_config.py` | 模板化单体进料 |
| `simulate_template_semibatch_ode.solver_mode` | explicit_bounded | - | `dynamic_template_reactor.py` | 默认稳定显式有界模式 |
| `posterior.n_steps` | 120 | steps | `posterior.py` | 研发级轻量MCMC默认步数 |
| `constrained_window.fouling limit` | 3.0 | - | `constrained_window.py` | 高挂胶风险硬约束 |
| `constrained_window.pressure drop limit` | 1000 | kPa | `constrained_window.py` | 输送压降硬约束 |
| `CFD grid convergence grids` | 40x20, 80x40 | cells | `cfd/grid_convergence.py` | 默认快速网格独立性诊断 |
| `ReproPackage app_version` | V4.7 / 0.5.4 | - | `repro_package.py` | 复现实验包版本 |

V4.7 验收结果：

```text
python -m py_compile app.py epdm_sim/**/*.py scripts/**/*.py -> passed
python -m pytest tests/test_template_config.py tests/test_feed_adapter.py tests/test_template_flowsheet.py \
  tests/test_ode_events.py tests/test_equation_code_consistency.py tests/test_posterior.py \
  tests/test_constrained_window.py tests/test_audit_trail.py tests/test_workflow_wizard.py \
  tests/test_cfd_grid_convergence.py -q -> 14 passed
python -m pytest -q -> 186 passed
python scripts/smoke_app.py -> smoke ok
http://127.0.0.1:8501/ -> HTTP 200
```

V4.7 已知局限性：

- EPDM 主流程仍以 validated legacy flowsheet 为工业应用适配层；generic template flowsheet 是轻量表观模型，不代表已校准工业体系。
- `solve_ivp` 当前作为动态模板反应器的模式接口和能力探针；完整模板状态导数仍应在 V4.8 中迁移到真正 solve_ivp 求解路径。
- 后验采样是研发级 proxy likelihood，不是严格贝叶斯反应器模型后验。
- 工程约束窗口使用快速 flowsheet 复核，仍需实验和动态/CFD复核。
- CFD grid convergence 是简化二维/准三维可视化模型的网格诊断，不等于工业CFD网格无关性证明。

V4.8 下一步建议：

- 将 `TemplateProcessConfig` 接入 UI 全局输入，实现按模板自动生成单体/CTA 进料编辑器。
- 将完整 template state derivative 移入 `solve_ivp`，支持事件终止、刚性BDF和质量矩阵扩展。
- 用真实 `flowsheet_real` / `dynamic_ode_real` likelihood 替换 posterior proxy。
- 增加 equation registry 与函数映射的静态扫描，确保每个 critical equation 都有对应代码检查。
- 将 audit trail 写入 SQLite，并在 UI 中提供历史运行查询和 manifest 对比。

### V4.6 / 0.5.3 dynamic template reactor, equation registry and reproducibility package

#### V4.6 vs V4.5

V4.6 相比 V4.5 的更新：

- 新增 `epdm_sim/state_vector.py`：通过 `StateVectorLayout` 将 reaction template 映射为 `liquid_moles[monomer]`、`gas_moles[component]`、`segment_masses[segment]`、`chain_transfer_moles[agent]` 和标量状态，支持 pack/unpack 和非负校验。
- 新增 `epdm_sim/dynamic_template_reactor.py`：实现 `simulate_template_semibatch_ode()`，用模板驱动的状态字典运行动态半连续釜式轨迹；EPDM默认模板继续输出 `C_E/C_P/C_ENB`、`conversion_E/P/ENB`、`C2/C3/ENB wt%` 兼容列，generic模板不依赖ENB字段也能运行。
- 新增 `epdm_sim/kpi_schema.py` 与 `epdm_sim/kpi_adapter.py`：将 flowsheet KPI 适配为 template-aware KPI rows，同时保留 EPDM application KPI aliases。
- 新增 `data/equation_registry.json`、`epdm_sim/equation_registry.py` 与 `epdm_sim/dimensional_checks.py`：把 Arrhenius、活化、ENB压力惩罚、乙烯竞争、氢调、反应热、绝热温升、Wilson K、Rachford-Rice、PR/SRK fugacity K、Henry Cstar、流变、压降、挂胶、Fox Tg 和牌号匹配等核心公式升级为机器可读注册表，并提供量纲检查。
- 新增 `epdm_sim/time_series_data.py` 与 `epdm_sim/profile_alignment.py`：支持实验时间序列导入、schema校验、模型曲线对齐、残差、RMSE/MAE/bias 计算。
- 新增 `epdm_sim/bayesian_doe.py`：基于弱参数、不确定性和工程约束对下一批实验进行候选排序，避免 preflight fail、`cooling_margin <= 0`、高挂胶、高压降和高固含不可行点。
- 新增 `data/property_sources.json` 与 `epdm_sim/property_confidence.py`：为物性值记录来源、适用范围、不确定度和置信等级，并将默认估算物性显式降权。
- 新增 `epdm_sim/surrogate.py`：提供线性/ridge物理约束代理模型，训练后强制基本单调性，例如 H2增加时 Mw 不应升高、固含增加时黏度不应下降、温度升高时黏度不应上升。
- 新增 `epdm_sim/repro_package.py`：导出审计级可复现实验包，包含 `manifest.json`、配置、参数集、reaction template、model/equation registry快照、KPI、守恒、工程规则、模型审计、环境和测试状态。
- `ui_workflow.py` 和 `TaskService` 注册 V4.6 新动作：`run_dynamic_template_ode`、`run_time_series_fit`、`run_bayesian_doe`、`train_surrogate`、`validate_surrogate`、`export_repro_package`，仍保持按钮触发和导出不重跑重模型原则。
- `report.py` Excel新增 `template_kpis`、`equation_registry`、`dimensional_checks`、`time_series_data`、`profile_residuals`、`bayesian_doe`、`property_confidence`、`property_conf_score`、`surrogate_model`、`surrogate_validation`、`repro_manifest` sheets。
- 新增审计文档：`docs/V4_6_FULL_AUDIT.md`。

V4.6 新增/修改模块：

- 新增：`epdm_sim/state_vector.py`、`epdm_sim/dynamic_template_reactor.py`、`epdm_sim/kpi_schema.py`、`epdm_sim/kpi_adapter.py`、`epdm_sim/equation_registry.py`、`epdm_sim/dimensional_checks.py`、`epdm_sim/time_series_data.py`、`epdm_sim/profile_alignment.py`、`epdm_sim/bayesian_doe.py`、`epdm_sim/property_confidence.py`、`epdm_sim/surrogate.py`、`epdm_sim/repro_package.py`
- 新增数据：`data/equation_registry.json`、`data/property_sources.json`
- 修改：`epdm_sim/report.py`、`epdm_sim/ui_workflow.py`、`epdm_sim/services/task_service.py`、`epdm_sim/__init__.py`、`README.md`
- 新增测试：`tests/test_state_vector.py`、`tests/test_dynamic_template_reactor.py`、`tests/test_kpi_schema.py`、`tests/test_equation_registry.py`、`tests/test_dimensional_checks.py`、`tests/test_time_series_data.py`、`tests/test_profile_alignment.py`、`tests/test_bayesian_doe.py`、`tests/test_property_confidence.py`、`tests/test_surrogate.py`、`tests/test_repro_package.py`
- 废弃：无。

V4.6 核心公式和数理约束：

```text
Template dynamic state:
  state = {liquid_moles[monomer], gas_moles[component],
           segment_masses[segment], chain_transfer_moles[agent],
           solvent_mass_kg, polymer_mass_kg, T_K, P_Pa,
           catalyst_active_mol, time_min}

Template dynamic rates:
  r_i = k_i,eff(T,P,C) * C_i * Cstar
  consumed_i <= available_i
  d(segment_mass_j)/dt = consumed_i * MW_i / 1000
  polymer_mass = sum(segment_masses)

Generic KPI schema:
  KPI = {name, value, unit, category, template_id,
         component_or_segment, compatibility_alias, bounds, warning}
  composition_sum ~= 100 wt%
  conversion in [0,100] %

Equation registry:
  equation_id -> formula_text + variable_units + output_unit
  dimensional checks cover kJ/h->kW, kg/h->mol/h, Pa<->MPa,
  wt%<->fraction and mol/L<->mol/m3.

Time-series calibration:
  aligned_model(t_exp) = interpolation(model_profile, t_exp)
  residual = model - experiment
  RMSE = sqrt(mean(residual^2))
  MAE = mean(abs(residual))

Bayesian/uncertainty DOE proxy:
  score = information_gain(parameter_uncertainty, candidate gradients)
          * feasibility_filter(preflight, cooling, fouling, pressure drop, solids)

Physical surrogate:
  y_hat = intercept + X * beta
  sign constraints:
    dMw/dH2 <= 0
    dviscosity/dsolids >= 0
    dviscosity/dT <= 0
    dheat_duty/dconversion >= 0

Repro package:
  manifest hashes = sha1(config, parameter_set, model_registry,
                         equation_registry, KPI snapshot)
```

V4.6 默认关键参数与适用范围：

| 参数/对象 | 默认值 | 单位 | 所在模块 | 说明 |
|---|---:|---|---|---|
| `StateVectorLayout.scalar_fields` | solvent/polymer/T/P/catalyst/time | mixed | `state_vector.py` | 模板动态状态标量 |
| `simulate_template_semibatch_ode(dt_min)` | 1.0 | min | `dynamic_template_reactor.py` | 显式有界动态积分步长 |
| `equation_registry.version` | V4.6 | - | `data/equation_registry.json` | 机器可读公式版本 |
| `property_sources.version` | V4.6 | - | `data/property_sources.json` | 物性来源版本 |
| `Bayesian DOE seed` | 11 | - | `bayesian_doe.py` | 可复现候选排序 |
| `surrogate ridge_alpha` | 1e-6 | - | `surrogate.py` | 线性代理正则化 |
| `ReproPackage app_version` | V4.6 / 0.5.3 | - | `repro_package.py` | 复现实验包版本 |

V4.6 验收结果：

```text
python -m py_compile app.py epdm_sim/**/*.py scripts/**/*.py -> passed
python -m pytest -q                                          -> 172 passed
```

V4.6 已知局限性：

- `dynamic_template_reactor.py` 使用显式有界积分器，适合研发趋势筛查，不等同于严格刚性ODE求解器。
- generic reaction template 仍是可运行接口和有限正值工程proxy，不代表任何具体工业聚合体系。
- Bayesian DOE 是弱参数/不确定性/工程约束排序，不是严格贝叶斯后验或D-optimal求解。
- surrogate 模型只可用于训练范围内快速筛选，不能替代 flowsheet 或 dynamic ODE 复核。
- `flowsheet.py` 和 Vistalon-like 对标仍以 EPDM 应用层为主，非EPDM模板需要新的目标牌号与产品规则。

V4.7 下一步建议：

- 将 `flowsheet.py` 主结果对象升级为 template-aware result，同时把 EPDM KPI 放到 application adapter。
- 将 `dynamic_template_reactor.py` 增加可选 `solve_ivp` stiff solver、事件函数和真实 recipe profile。
- 将 CFD scalar 字段从固定 EPDM 名称扩展为 template scalar labels。
- 将 SQLite 数据仓库与 repro package 连接，生成数据快照ID和参数集签名。
- 引入真实时间序列实验样例，验证 profile alignment、动态参数估计和量热闭合。

### V4.5 / 0.5.2 templated kinetics, property models, rheology and model audit

#### V4.5 vs V4.4

V4.5 相比 V4.4 的更新：

- 模板化动力学内核：`kinetics.py` 新增 `RateResult.rates_mol_L_h`、`effective_rate_constants`、`concentration_basis`、`modifiers` 和 `warnings`，并新增 `calculate_template_rates()`、`calculate_template_conversions()`、`calculate_template_polymer_segments()`。
- `reactor.py` 在默认快速反应器中优先读取 reaction template 的 monomers、segment map、molecular weights 和 heat of polymerization，同时保留 `r_E/r_P/r_ENB` 与 `C2/C3/ENB` 兼容输出。
- `data/reaction_templates.json` 升级到 V4.5，`property_model` 从字符串升级为结构化字段，包含 composition、Mw、viscosity、thermal、crystallization 和 Mooney 模型声明。
- 新增 `epdm_sim/property_models.py`：`predict_polymer_properties()` 按 template 的 `property_model.model_id` 分发 EPDM经验模型或generic有限正值模型。
- 新增 `epdm_sim/calibration_loop.py`：串联已有实验覆盖、参数可辨识性、不确定性和DOE建议，输出弱参数、预期信息增益和风险降低方向。
- 新增 `epdm_sim/rheology.py`：统一 Newtonian、power-law、Carreau-Yasuda 和 EPDM empirical solution viscosity；`fluid_props.py` 的 apparent viscosity 已转向该模块。
- `flash.py` 新增 `FlashDiagnostic` 与 `diagnose_flash_result()`，检查 vapor fraction、fallback、轻/重组分分配和 polymer pseudo 非挥发性。
- 新增 `epdm_sim/model_audit_report.py`：将模型可信度、preflight、守恒、工程检查、可辨识性、不确定性、数据质量、校准和任务新鲜度汇总为可复现审计报告。
- `ui_workflow.py` 新增 `run_calibration_loop` action，保持校准闭环为按钮触发的轻量任务，不触发ODE/CFD/优化。
- `report.py` Excel新增 `kinetics_template`、`property_model`、`calibration_loop`、`rheology`、`flash_diagnostics`、`model_audit`、`model_audit_risks`、`model_audit_actions` sheets。
- 新增审计文档：`docs/V4_5_FULL_AUDIT.md`。

V4.5 新增/修改模块：

- 新增：`epdm_sim/property_models.py`、`epdm_sim/calibration_loop.py`、`epdm_sim/rheology.py`、`epdm_sim/model_audit_report.py`
- 修改：`data/reaction_templates.json`、`epdm_sim/kinetics.py`、`epdm_sim/reactor.py`、`epdm_sim/polymer_props.py`、`epdm_sim/fluid_props.py`、`epdm_sim/flash.py`、`epdm_sim/ui_workflow.py`、`epdm_sim/report.py`、`README.md`
- 新增测试：`tests/test_v4_5_kinetics_template.py`、`tests/test_property_models.py`、`tests/test_calibration_loop.py`、`tests/test_rheology.py`、`tests/test_flash_diagnostics.py`、`tests/test_model_audit_report.py`
- 废弃：无。

V4.5 核心公式和数理约束：

```text
参数估计-不确定性-DOE闭环:
  experiment data -> identifiability -> uncertainty -> DOE recommendation
  -> information gain / risk reduction ranking

Template kinetics:
  r_i = k_i,eff(T,P,C) * C_i * Cstar
  conversion_i = min(consumed_i, feed_i) / feed_i
  segment_mass_j = sum(consumed_i * MW_i / 1000)

EPDM ENB modifiers:
  pressure_factor_ENB = 1 / (1 + beta_P * max(P_MPa - 0.7, 0))
  ethylene_competition_factor = 1 / (1 + beta_E * C_E / max(C_ENB, tiny))

Rheology:
  mu0 = mu_solvent_ref * exp(E_mu/R*(1/T - 1/T_ref))
        * exp(A_mu*solids + B_mu*solids^2)
        * (Mw/300000)^alpha_Mw
  power-law:       mu_app = K * gamma_dot^(n-1)
  Carreau-Yasuda:  mu_app = mu_inf + (mu0-mu_inf)*(1+(lambda*gamma_dot)^a)^((n-1)/a)

Model audit:
  overall_score 仍由 data/model/numerical/engineering/calibration/freshness/
  engineering_rule/identifiability/uncertainty 加权构成；V4.5新增审计表追踪风险和下一步动作。
```

V4.5 默认关键参数：

| 参数 | 默认值 | 单位 | 所在模块 | 说明 |
|---|---:|---|---|---|
| `k_E_ref` | 3.6e6 | L/mol/h | `kinetics.py` | 乙烯表观插入常数 |
| `k_P_ref` | 1.45e6 | L/mol/h | `kinetics.py` | 丙烯表观插入常数 |
| `k_ENB_ref` | 4.0e6 | L/mol/h | `kinetics.py` | ENB表观插入常数 |
| `beta_P` | 0.35 | 1/MPa | `kinetics.py` | 高压ENB引入惩罚 |
| `beta_E` | 0.01 | - | `kinetics.py` | 乙烯竞争插入惩罚 |
| `A_mu` | 8.0 | - | `rheology.py`/`fluid_props.py` | 固含一阶黏度指数 |
| `B_mu` | 15.0 | - | `rheology.py`/`fluid_props.py` | 固含二阶黏度指数 |
| `alpha_Mw` | 0.6 | - | `rheology.py`/`fluid_props.py` | 分子量黏度指数 |
| `power_law_n` | 0.72 | - | `rheology.py` | 剪切变稀指数 |
| `carreau_lambda_s` | 1.2 | s | `rheology.py` | Carreau特征时间 |

V4.5 验收结果：

```text
python -m py_compile app.py epdm_sim/**/*.py scripts/**/*.py -> passed
python -m pytest -q                                          -> 155 passed
```

V4.5 已知局限性：

- `dynamic_reactor.py` 的详细ODE profile 仍以 EPDM 字段输出，尚未完全泛化为任意 monomer state vector。
- `flowsheet.py` 的KPI仍保留 `C2_wt/C3_wt/ENB_wt`、Vistalon-like 对标等EPDM应用层字段。
- generic property model 是有限正值工程proxy，不代表通用聚合物物性包。
- calibration loop 的 expected information gain 是启发式排序，不是严格D-optimal或Bayesian DOE。
- FlashDiagnostic 是相平衡 sanity check，不替代完整聚合物溶液VLE模型。

V4.6 下一步建议：

- 将 `dynamic_reactor.py` 内部ODE状态向量改为 `liquid_moles[monomer]`、`gas_moles[component]`、`segment_masses[segment]`。
- 将 `flowsheet.py` KPI输出分为 generic KPI 与 EPDM application KPI 两层。
- 将 DOE optimal 升级为约束D-optimal/Bayesian实验设计，并与SQLite实验仓库形成闭环。
- 将 CFD scalar 字段名称从固定 E/P/ENB 扩展为 template scalar labels。
- 将 report export 与 TaskService 的结果新鲜度状态做更强绑定。

### V4.4 / 0.5.1 template-driven execution, preflight and identifiability

#### V4.4 vs V4.3

V4.4 相比 V4.3 的更新：

- 反应模板深度接入：`reactor.py` 的默认 monomer 列表和 segment map 来自 `reaction_templates.py`；`heat_balance.py` 默认 `deltaH_polymerization` 来自 `data/reaction_templates.json`；`conservation.py` 的 segment balance 支持模板化 segment map。
- 新增 `epdm_sim/preflight.py`：模型运行前校验温度、压力、进料、停留时间、溶剂、CSTR数量、purge、U/A、管径、CFD输入和优化边界。
- `simulation_service.py` 在快速 flowsheet 前执行 preflight；`TaskService.run()` 支持可选 preflight，失败时不运行重任务并记录错误。
- 守恒闭合升级为诊断：`conservation.py` 新增 `ConservationDiagnostic`，可定位 flash、heat_balance、product_properties、recycle_solver 或 component balance。
- 新增 `epdm_sim/identifiability.py`：有限差分敏感度、Fisher 信息矩阵 proxy、参数相关性、condition number 和可辨识性分级。
- 新增 `epdm_sim/doe_optimal.py`：推荐下一批实验点，覆盖压力、ENB、H2、温度、Al/Ti、BHT、乙烯富集和rpm，同时过滤 `cooling_margin <= 0` 或 `fouling_index >= 3` 的不可行点。
- 新增 `epdm_sim/thermo_consistency.py`：检查 EOS K值、Z、phi、Henry压力单调性、Flash降压/升温趋势和聚合物非挥发。
- 新增 `epdm_sim/dynamic_stability.py`：检查动态ODE profile 的非负状态、温度边界、固含/聚合物非下降、淬灭/失活后放热下降和有限性。
- `model_confidence.py` 扩展评分维度：`preflight_score`、`conservation_score`、`engineering_rule_score`、`identifiability_score`、`uncertainty_score`、`validation_data_score`。
- `report.py` 新增 sheets：`preflight`、`conservation_diag`、`identifiability`、`param_correlation`、`doe_optimal`、`thermo_consistency`、`dynamic_stability`、`ui_task_governance`。
- 新增审计文档：`docs/V4_4_FULL_AUDIT.md`。

V4.4 新增/修改模块：

- 新增：`epdm_sim/preflight.py`、`epdm_sim/identifiability.py`、`epdm_sim/doe_optimal.py`、`epdm_sim/thermo_consistency.py`、`epdm_sim/dynamic_stability.py`
- 修改：`epdm_sim/reaction_templates.py`、`epdm_sim/reactor.py`、`epdm_sim/heat_balance.py`、`epdm_sim/conservation.py`、`epdm_sim/model_confidence.py`、`epdm_sim/report.py`、`epdm_sim/services/simulation_service.py`、`epdm_sim/services/task_service.py`、`app.py`、`README.md`
- 新增测试：`tests/test_preflight.py`、`tests/test_v4_4_templates.py`、`tests/test_conservation_diagnostics.py`、`tests/test_identifiability.py`、`tests/test_doe_optimal.py`、`tests/test_thermo_consistency.py`、`tests/test_dynamic_reactor_stability.py`
- 废弃：无。

V4.4 前置输入校验（preflight）：

| 模型 | 检查内容 | 阻断条件 |
|---|---|---|
| flowsheet | T、P、feed、tau、solvent、num_cstr、purge、U、A、pipe D | 非有限、负值、越界、未知溶剂 |
| CFD | Nx/Ny、rho、mu、Cp、k、几何、热源、rpm | 非有限、非正物性/几何、网格不合理 |
| optimizer | bounds、目标牌号 | lower>=upper 或目标牌号不存在 |

V4.4 参数可辨识性逻辑：

| 参数 | 需要的数据变化 | 若缺失则 |
|---|---|---|
| beta_P | 压力梯度 | weakly_identifiable |
| beta_E | C_E/C_ENB 梯度 | weakly_identifiable |
| ktr_H2 | H2 梯度 | weakly_identifiable |
| kd_h | 时间或停留时间梯度 | weakly_identifiable |

V4.4 模型可信度评分：

```text
overall =
  0.12*data_score
  + 0.13*model_score
  + 0.16*numerical_score
  + 0.13*engineering_score
  + 0.11*calibration_score
  + 0.10*freshness_score
  + 0.09*engineering_rule_score
  + 0.08*identifiability_score
  + 0.08*uncertainty_score
```

其中：

- `numerical_score` 由 preflight 和 conservation 共同决定；
- `engineering_rule_score` 由趋势规则失败/警告决定；
- `identifiability_score` 由弱可辨识和不可辨识参数数量决定；
- `uncertainty_score` 未运行不确定性分析时降低；
- 默认参数集未校准时降低 calibration_score。

V4.4 验收结果：

```text
python -m py_compile app.py epdm_sim/**/*.py scripts/**/*.py -> passed
python -m pytest                                             -> 136 passed
```

V4.4 已知局限性：

- 反应模板已接入 reactor/heat_balance/conservation，但 kinetics 和 polymer_props 仍保留 EPDM 特化输出字段。
- 参数可辨识性使用有限差分 proxy，不等同于严格统计FIM。
- DOE optimal 是工程可行性推荐，不自动生成真实实验配方SOP。
- 热力学一致性检查是 sanity check，不替代真实 VLE/溶解度实验。
- 动态ODE稳定性检查是 profile 后验诊断，真实压力控制和气相headspace仍为简化。

V4.5 下一步建议：

- 将 `kinetics.py` 速率对象从 `r_E/r_P/r_ENB` 抽象为任意 monomer rates。
- 将 `polymer_props.py` 属性模型按 reaction template/property_model 分发。
- 将 DOE optimal 与 parameter_estimation 真实残差、uncertainty 和实验数据仓库闭环。
- 增加真实实验时间序列导入，与 dynamic ODE 做 profile alignment。
- 把 UI action registry 与页面按钮做强绑定测试，确保所有重任务都走 TaskService。

### V4.3 / 0.5.0 conservation, rule governance and confidence score

本次更新目标：让所有模块更具普适性，并用显式的数理/化工逻辑检查约束结果。V4.3 不重建项目、不删除现有功能，而是在当前 V4.1.2 主项目上增加治理层，使流程模拟、动态釜式模型、热力学、流体、CFD、参数估计、案例和报告都能被审计。

V4.3 相比 V4.1.2 的更新：

- 新增 `epdm_sim/conservation.py`：守恒闭合框架，覆盖总物料、组分、反应器单体-聚合物、E/P/D segment、Flash、聚合热、产品组成和回收循环闭合。
- 新增 `data/engineering_rules.json` 与 `epdm_sim/engineering_rules.py`：化工趋势规则库，覆盖 H2-Mw/门尼、固含-黏度、温度-黏度、Mw-黏度、压降、反应热、闪蒸、ENB压力/进料、Al/Ti、BHT和产品组成。
- 新增 `epdm_sim/io_schema.py`：统一 IO schema，声明每个核心模型的输入、输出、单位、类型、范围和物理边界，可导出为 Excel sheet。
- 新增 `epdm_sim/numerics.py`：数值稳定性工具，统一 finite、nonnegative、bounded、normalize、safe exp/log/power 和 KPI 有限性检查。
- 新增 `epdm_sim/ui_workflow.py`：UI action registry，明确每个按钮/导入/导出动作的触发类型、依赖、读写、失效对象和预计耗时。
- 新增 `epdm_sim/ui_audit.py`：页面静态审计，扫描 `app.py` 和 `epdm_sim/pages/*.py` 是否存在页面加载即运行重任务、入口过厚或缺少工程化错误路径。
- 新增 `epdm_sim/model_confidence.py`：模型可信度卡片，按数据、模型、数值、工程、校准和结果新鲜度给出 0-100 分。
- 新增 `data/reaction_templates.json` 与 `epdm_sim/reaction_templates.py`：反应模板接口，默认模板为 `EPDM_EPM_metallocene_solution`，并预留通用溶液共聚和三元共聚模板。
- 新增 `docs/V4_3_FULL_AUDIT.md`：记录当前项目结构、legacy关系、模型假设、输入/输出/单位、守恒/趋势覆盖、UI触发路径、硬编码点和下一步开发优先级。
- 升级 `data/model_registry.json` 到 `0.5.0`，新增 `model_governance_v43` 模块，记录 V4.3 治理层公式、输入输出、单位、检查和触发策略。
- 升级 `app.py`：性能诊断面板新增守恒闭合、模型可信度、化工趋势规则库和 UI 点击动作注册表；趋势规则必须按钮触发。
- 升级 `epdm_sim/report.py`：Excel新增 `conservation`、`engineering_rules`、`io_schema`、`ui_actions`、`ui_audit`、`model_confidence_card`、`reaction_templates` sheets；Word/PDF新增守恒闭合和模型可信度摘要。

V4.3 新增/修改模块：

- 新增：`epdm_sim/conservation.py`、`epdm_sim/engineering_rules.py`、`epdm_sim/io_schema.py`、`epdm_sim/numerics.py`、`epdm_sim/ui_workflow.py`、`epdm_sim/ui_audit.py`、`epdm_sim/model_confidence.py`、`epdm_sim/reaction_templates.py`
- 新增数据：`data/engineering_rules.json`、`data/reaction_templates.json`
- 新增文档：`docs/V4_3_FULL_AUDIT.md`
- 修改：`app.py`、`epdm_sim/report.py`、`epdm_sim/services/task_service.py`、`data/model_registry.json`、`README.md`
- 新增测试：`tests/test_conservation.py`、`tests/test_engineering_rules.py`、`tests/test_io_schema.py`、`tests/test_numerics.py`、`tests/test_ui_workflow.py`、`tests/test_ui_audit.py`、`tests/test_model_confidence.py`、`tests/test_reaction_templates.py`
- 废弃：无。

V4.3 守恒闭合框架：

| 检查 | 参考量 | 计算量 | 默认容差 | 工程含义 |
|---|---|---|---:|---|
| total_mass_balance | Feed kg/h | Product + Flash vapors kg/h | 1% | 全流程总物料闭合 |
| component_mass_balance | 组分进料 kg/h | 分子出口 + 聚合段 kg/h | 1% | C2/C3/ENB/H2/溶剂闭合 |
| reactor_monomer_polymer_balance | consumed mol × MW | polymer kg/h | 0.5% | 单体消耗生成聚合物 |
| segment_balance | polymer kg/h | E+P+D kg/h | 0.5% | 聚合段质量归一 |
| flash_mass_balance | flash inlet kg/h | vapor + liquid kg/h | 0.5% | 闪蒸单元闭合 |
| energy_release_balance | Σn_i×abs(ΔH_i) | Q_rxn kJ/h | 0.5% | 聚合热符号和量纲正确 |
| product_composition_balance | 100 wt% | C2+C3+ENB wt% | 0.5% | 产品组成闭合 |
| recycle_balance | 0 kg/h | recycle closure kg/h | 1 kg/h | 回收迭代闭合 |

V4.3 化工趋势规则库：

| rule_id | 预期趋势 | 数理/化工逻辑 |
|---|---|---|
| h2_mw_decreases | H2↑ -> Mw↓或不升 | 氢气链转移降低链长 |
| h2_mooney_decreases | H2↑ -> Mooney↓或不升 | 门尼随Mw降低而下降 |
| solids_viscosity_increases | solids↑ -> μ↑ | 聚合物固含提高溶液黏度 |
| temperature_viscosity_decreases | T↑ -> μ↓ | Arrhenius黏温关系 |
| mw_viscosity_increases | Mw↑ -> μ↑ | 高分子链缠结增强 |
| pipe_diameter_drop_increases | D↓ -> ΔP↑ | Darcy-Weisbach L/D 和速度项 |
| flow_drop_increases | Q↑ -> ΔP↑ | 流速升高导致动压上升 |
| conversion_heat_increases | consumed↑ -> Q_rxn↑ | 聚合热正比单体消耗 |
| flash_pressure_vapor_increases | P_flash↓ -> V↑ | 降压提高轻组分气化 |
| polymer_stays_liquid | polymer vapor≈0 | 聚合物伪组分非挥发 |
| high_pressure_enb_not_raise | 0.7->2.0MPa ENB不异常升高 | PDF规律：低压有利于ENB结合 |
| enb_feed_enb_wt_increases | ENB feed↑ -> ENB wt%↑ | ENB投料提高产品二烯含量 |
| low_alti_activity_drops | Al/Ti低 -> 产率低 | MAO活化不足 |
| bht_activity_nonnegative | BHT不导致负活性 | 活性修正必须非负 |
| product_composition_100 | C2+C3+ENB≈100 | 聚合段组成归一 |

V4.3 UI点击治理：

| action_id | trigger_type | target_task | 说明 |
|---|---|---|---|
| run_fast_flowsheet | auto_cached | flowsheet_fast | 快速流程、热量、流体、产品KPI |
| run_dynamic_ode | button_manual | dynamic_ode | 动态釜式ODE，不随页面切换运行 |
| run_cfd | button_manual | cfd | CFD场计算，不随滑块运行 |
| run_optimizer / run_pareto | button_manual | optimization | 优化/Pareto必须按钮触发 |
| run_parameter_estimation | button_manual | parameter_estimation | 参数拟合失败不覆盖默认参数 |
| run_uncertainty | button_manual | uncertainty | 不确定性分析手动触发 |
| export_excel / export_word / export_openfoam | export | report_export/openfoam_export | 导出读取已有结果，缺失重任务写“未运行” |
| run_engineering_rules | button_manual | engineering_rules | 趋势规则一键诊断 |
| run_conservation_checks | auto_cached | conservation | 轻量守恒检查随快速结果复用 |

V4.3 反应模板接口：

| template_id | 用途 | 状态 |
|---|---|---|
| EPDM_EPM_metallocene_solution | 当前默认EPDM/EPM茂金属溶液聚合模板 | active |
| generic_solution_copolymerization | 未来二元溶液共聚接口 | scaffold |
| generic_terpolymerization_apparent | 未来三元表观共聚接口 | scaffold |

默认 `EPDM_EPM_metallocene_solution` 参数：

| 项目 | 默认值 | 单位 |
|---|---:|---|
| ΔH_ethylene | -95 | kJ/mol |
| ΔH_propylene | -85 | kJ/mol |
| ΔH_ENB | -80 | kJ/mol |
| segment map | ethylene->E, propylene->P, ENB->D | - |
| chain transfer agent | hydrogen | - |
| validity range | 60-180 °C, 0.1-5 MPa | 工程筛选 |

V4.3 验收结果：

```text
python -m py_compile app.py epdm_sim/**/*.py scripts/**/*.py -> passed
python -m pytest                                             -> 116 passed
python scripts/smoke_app.py                                  -> smoke ok
```

V4.3 已知局限性：

- 守恒闭合检查是后验一致性检查，不会自动修正模型。
- 趋势规则库使用快速流程和轻量物性模型，不代表工业精度验证。
- 反应模板接口已建立，但 `kinetics.py/reactor.py/heat_balance.py` 尚未完全模板化。
- 模型可信度评分是工程化筛查分数，不是统计置信度或工业认证。
- CFD仍是研发级二维/准三维趋势模型，不等同于真实三维搅拌釜CFD。

V4.4 下一步建议：

- 将 reaction template 深度接入 kinetics/reactor/heat_balance，减少EPDM硬编码。
- 让工程趋势规则按 catalyst family、solvent 和 reactor scale 分组。
- 将守恒闭合和模型可信度与参数估计/不确定性结果联动。
- 增强动态ODE的气相headspace、PID控制和实验时间序列对齐。
- 继续提升OpenFOAM reactor case从 skeleton 到可运行网格。

### V4.1.2 / 0.4.6 physical folder consolidation

本次更新目标：按“两个文件夹合并”的物理目录要求，把 `D:\codex\metallocene-epdm-process-simulator` 整个迁入 `D:\codex\metallocene-epdm-digital-twin` 内部，不再保留两个并列项目文件夹。

V4.1.2 相比 V4.1.1 的更新：

- 外层 `D:\codex` 现在只保留一个主项目文件夹：`metallocene-epdm-digital-twin`。
- 旧项目完整迁入：

```text
D:\codex\metallocene-epdm-digital-twin\legacy_archive\metallocene-epdm-process-simulator
```

- 旧项目原始应用仍保留为 `legacy_app.py`，可用于审计/对比。
- 旧项目归档内的 `app.py` 仍是兼容启动器，会定位并启动上层 `metallocene-epdm-digital-twin\app.py`。
- 更新 `legacy_archive\metallocene-epdm-process-simulator\README.md` 和 `docs/MERGED_PROJECTS.md`，明确物理合并后的路径。
- `pyproject.toml` 仍只收集主项目 `tests/`，归档旧测试不会干扰主线验收。

物理合并后的推荐运行方式：

```powershell
cd D:\codex\metallocene-epdm-digital-twin
streamlit run app.py
```

归档兼容入口：

```powershell
cd D:\codex\metallocene-epdm-digital-twin\legacy_archive\metallocene-epdm-process-simulator
streamlit run app.py
```

验收结果：

```text
digital-twin py_compile                              -> passed
digital-twin pytest                                  -> 89 passed
digital-twin smoke_app                               -> smoke ok
legacy archive app.py + legacy_app.py py_compile     -> passed
outer D:\codex project folders                        -> only metallocene-epdm-digital-twin remains
```

### V4.1.1 / 0.4.5 physical project merge entrypoint

本次更新目标：把 `metallocene-epdm-process-simulator` 从“逻辑合并/归档来源”进一步处理为“实际兼容入口”，避免用户误开旧版 MVP。

V4.1.1 相比 V4.1 的更新：

- `D:\codex\metallocene-epdm-process-simulator\app.py` 已替换为兼容启动器，执行 `streamlit run app.py` 时会启动 `metallocene-epdm-digital-twin` 主应用。
- 旧 `process-simulator` 原始 Streamlit 应用已保留为 `legacy_app.py`，不删除历史功能，可用于审计和对照。
- `metallocene-epdm-process-simulator\README.md` 已更新，明确主项目路径、统一运行方式和 legacy 归档入口。
- 新增 `metallocene-epdm-process-simulator\MERGED_INTO_DIGITAL_TWIN.md`。
- 更新 `docs/MERGED_PROJECTS.md`，记录兼容启动器和旧项目归档策略。

合并后的运行规则：

```powershell
cd D:\codex\metallocene-epdm-digital-twin
streamlit run app.py
```

或兼容旧路径：

```powershell
cd D:\codex\metallocene-epdm-process-simulator
streamlit run app.py
```

两者均进入 `metallocene-epdm-digital-twin` 主应用。旧版早期MVP仅通过：

```powershell
streamlit run legacy_app.py
```

验收结果：

```text
python -m py_compile app.py epdm_sim/**/*.py scripts/**/*.py -> passed
python -m pytest                                             -> 89 passed
python scripts/smoke_app.py                                  -> smoke ok
legacy compatibility app.py                                  -> py_compile passed
```

### V4.1 / 0.4.4 universal model contracts, engineering checks and click workflow

本次更新目标：在已合并 `metallocene-epdm-process-simulator` 的 V4.0.3 基础上，把平台进一步升级为 **“通用模型架构 + 数理化工逻辑校验 + 高效交互工作流”**。核心原则是：模型不为单一默认案例硬编码，所有关键计算有单位/量纲检查、守恒检查、工程趋势检查，重任务明确按钮触发。

V4.1 相比 V4.0.3 的更新：

- 新增 `epdm_sim/units.py`：提供 kg/h、mol/h、mol/L、mol/m3、MPa、Pa、degC、K、L、m3、kJ/h、kW、g/mol、kg/mol、wt% 和 fraction 的基础转换，以及温度、压力、质量流、组成、热负荷、转化率断言。
- 新增 `epdm_sim/model_contracts.py`：从模型注册表生成统一模型契约，字段包括 inputs、outputs、parameters、assumptions、validity_range、required_units、fallback_mode 和 validation_rules。
- 新增 `epdm_sim/model_validation.py`：检查模型契约是否缺失单位、校验规则、输入/输出、缓存/按钮触发策略。
- 新增 `epdm_sim/engineering_checks.py`：对流程结果执行物料衡算、反应器、热量、流体、闪蒸和产品组成工程逻辑检查。
- 升级 `data/model_registry.json`：每个 active 模块新增 `parameters`、`required_units`、`mathematical_checks`、`chemical_engineering_checks`、`computational_cost`、`ui_trigger_policy`、`ui_entry`。
- 升级 `epdm_sim/model_registry.py`：注册表校验现在强制 active 模块包含公式、单位、数理校验、化工校验、计算成本和 UI 触发策略。
- 升级 `epdm_sim/services/task_service.py`：任务记录扩展为 `input_hash`、`dependency_hash`、`cache_hit`、`stale_reason`、`last_error`，并新增统一 `TASK_GRAPH`。
- 升级 `app.py`：全局“性能诊断”中显示任务图、长任务状态和工程逻辑检查表；页面切换仍不触发 ODE/CFD/优化/参数估计。
- 升级 `epdm_sim/report.py`：Excel增加 `engineering_checks` 和 `model_contracts` sheets；Word/PDF增加工程检查和模型适用范围摘要。
- 新增数理趋势回归测试：H2-Mw/门尼、固含-黏度、温度-黏度、压力-ENB、ENB进料-产品ENB、反应热、压降、闪蒸、产品组成。

新增/修改模块：

- 新增：`epdm_sim/units.py`、`epdm_sim/model_contracts.py`、`epdm_sim/model_validation.py`、`epdm_sim/engineering_checks.py`
- 修改：`data/model_registry.json`、`epdm_sim/model_registry.py`、`epdm_sim/services/task_service.py`、`app.py`、`epdm_sim/report.py`、`README.md`
- 新增测试：`tests/test_units.py`、`tests/test_model_contracts.py`、`tests/test_model_validation.py`、`tests/test_engineering_checks.py`、`tests/test_engineering_trends.py`
- 废弃：无。

V4.1 模型普适性设计：

- 每个核心模块先通过 `data/model_registry.json` 声明公式、输入/输出、参数、单位、适用范围、fallback和UI触发策略。
- `ModelContract` 是统一适配层，避免未来每新增一个模型都在页面里堆计算逻辑。
- `engineering_checks` 对结果做化工逻辑后验校验，不替代模型，但能及时发现单位、守恒、趋势和边界条件问题。
- 所有重任务仍由 `TaskService` 显式按钮触发；快速流程模拟使用 hash cache。

V4.1 task graph：

| task_id | 触发方式 | 依赖 | 预计耗时 |
|---|---|---|---|
| flowsheet_fast | auto_cached | - | <0.5 s |
| dynamic_ode | button_manual | flowsheet_fast | 1-5 s |
| cfd | button_manual | flowsheet_fast | 1-4 s |
| parameter_estimation | button_manual | experiment_data | 3-30 s |
| optimization | button_manual | flowsheet_fast | 2-20 s |
| uncertainty | button_manual | flowsheet_fast | 2-20 s |
| report_export | button_manual | current_results | 1-10 s |

V4.1 新增验收结果：

```text
python -m py_compile app.py epdm_sim/**/*.py scripts/**/*.py -> passed
python -m pytest                                             -> 89 passed
```

### V4.0.3 project consolidation and model registry

本次更新目标：把 `metallocene-epdm-process-simulator` 与 `metallocene-epdm-digital-twin` 统一为一个主线项目。`digital-twin` 作为唯一运行入口，`process-simulator` 作为早期流程模拟基线和归档来源；合并采用“保留新实现、登记旧来源、验证模型适用范围”的方式，避免旧文件覆盖 V4 的动态釜式、校准、CFD、案例和报告能力。

V4.0.3 相比 V4.0.2 的更新：

- 新增 `data/model_registry.json`：统一登记流程、热力学、溶解度、反应器、热量衡算、流变/压降、产品预测、参数估计、CFD、优化、不确定性、数据/报告和 OpenFOAM 导出模块。
- 新增 `epdm_sim/model_registry.py`：提供模型注册表加载、校验、UI表格和触发策略摘要，保证每个模块有公式、输入、输出、适用范围、fallback和触发方式。
- 新增 `docs/MERGED_PROJECTS.md`：记录两个项目的合并清单，说明旧 process-simulator 数据、公式和测试如何映射到当前 V4 模块。
- 首页/侧边栏新增“模型模块与点击策略”：显示自动缓存模块、按钮触发模块、数据/导出模块，避免 ODE、CFD、优化、参数估计和报告导出随滑块误触发。
- 保留现有 `metallocene-epdm-digital-twin` 功能，不删除已有页面、测试、数据或报告能力；旧 `metallocene-epdm-process-simulator` 不再作为运行入口。

新增/修改模块：

- 新增：`epdm_sim/model_registry.py`
- 新增数据：`data/model_registry.json`
- 新增文档：`docs/MERGED_PROJECTS.md`
- 修改：`app.py`、`README.md`
- 新增测试：`tests/test_model_registry.py`
- 废弃：无；旧项目作为归档来源，不参与主应用启动。

技术核心变化：

- 模型触发方式分为 `auto_cached`、`button_manual`、`data_only`、`export_only`。
- `auto_cached` 只用于快速流程、热量、流体性质、闪蒸和产品预测等轻量计算。
- `button_manual` 用于 ODE、CFD、参数估计、优化/Pareto、不确定性和报告图导出。
- 每个模型条目都记录 `equations`、`inputs`、`outputs`、`validity_range`、`engineering_logic` 和 `fallback`，用于保证模块普适性、数理逻辑和化工适用性可审核。

验收结果：

```text
python -m py_compile app.py epdm_sim/**/*.py scripts/**/*.py -> passed
python -m pytest                                             -> 72 passed
```

### V4.0.2 Streamlit runtime compatibility hotfix

本次修复目标：解决当前本地运行环境中部分页面出现 `ModuleNotFoundError: No module named 'streamlit.emojis'` 的运行时崩溃，并补齐基础依赖环境，使测试和本地服务可复现。

更新内容：

- 修复当前 bundled Streamlit 运行包缺少 `streamlit.emojis` 时，`st.info()` / `st.success()` / `st.warning()` / `st.error()` 触发的页面级崩溃。
- 在 `ui_theme.py` 中新增 `install_safe_alerts()`，应用主题后自动将 Streamlit alert 替换为本项目自定义玻璃拟态提示组件。
- 保留原页面业务逻辑，不删除现有功能，不改变 ODE、CFD、优化、参数估计、报告导出的按钮触发策略。
- 本地 Python 环境缺少 `pytest` 时，已按 `requirements.txt` 补齐基础依赖；后续验收命令可直接运行。

涉及模块：

- 修改：`epdm_sim/ui_theme.py`
- 环境修复：按 `requirements.txt` 安装基础依赖，包括 `pytest`、`streamlit`、`scipy`、`plotly`、`matplotlib`、`networkx` 等。
- 废弃：无。

验收结果：

```text
python -m py_compile app.py epdm_sim/**/*.py scripts/**/*.py -> passed
python -m pytest                                             -> 69 passed
python scripts/smoke_app.py                                  -> smoke ok
streamlit run app.py                                         -> http://127.0.0.1:8501 returned HTTP 200
浏览器逐页巡检 13 个页面                                    -> all ok, no Traceback/error logs
按钮路径抽查                                                -> dynamic quick, ODE, parameter estimation,
                                                              case save, CFD, sensitivity, Pareto,
                                                              uncertainty, Excel report all ok
后端长任务直接调用                                          -> flowsheet, dynamic_fast, dynamic_ode,
                                                              CFD, optimizer, Pareto, uncertainty,
                                                              parameter estimation, Excel/Word report,
                                                              case package all ok
Streamlit stderr                                             -> no module/runtime Traceback after fix
```

### V4.0.1 runtime audit hotfix

本次修复目标：针对 Streamlit 实际页面运行时错误进行逐页巡检和修复，确保 V4 在浏览器中可稳定打开，而不只是通过单元测试。

更新内容：

- 修复“反应器与动力学”页面速率读取错误：`ReactorResult.rates` 是字典，页面已改为安全读取 `r_E / r_P / r_ENB`。
- 修复“产品性能与美孚Vistalon-like对标”页面 `Tm_C=None` 时的格式化崩溃；无熔融峰时显示“无熔融峰”。
- 修复 KPI/诊断表中数字、字符串、布尔值混合导致的 Streamlit/PyArrow 序列化 Traceback。
- 将页面中已弃用的 `use_container_width=True` 统一替换为 `width="stretch"`，减少后台日志噪声，便于后续定位真实错误。

涉及模块：

- 修改：`epdm_sim/pages/reactor_page.py`、`epdm_sim/pages/product_page.py`、`epdm_sim/pages/dashboard_page.py`
- 修改：`epdm_sim/heat_balance.py`、`epdm_sim/fluid_props.py`、`epdm_sim/services/simulation_service.py`
- 机械更新：`app.py` 与 `epdm_sim/pages/` 中的 Streamlit 宽度参数
- 废弃：无

验收结果：

```text
python -m py_compile app.py epdm_sim/**/*.py  -> passed
python -m pytest                              -> 69 passed
python scripts/smoke_app.py                   -> smoke ok
streamlit run app.py                          -> http://127.0.0.1:8501 returned HTTP 200
浏览器逐页巡检 13 个页面                     -> all ok, no Traceback/error logs
Streamlit stderr                              -> empty after hotfix page audit
```

### V4 vs V3

新增能力：

- 真实模型联合参数估计：`parameter_estimation.py` 支持 `model_mode=empirical_proxy / flowsheet_real / dynamic_ode_real / hybrid`，其中 `flowsheet_real` 调用 `run_flowsheet()`，`dynamic_ode_real` 调用 `simulate_dynamic_semibatch_ode()`。
- 参数估计预算控制：`max_nfev`、`max_seconds`、`early_stop`、`failed_run_penalty`、parameter-hash cache；输出 `model_mode`、`fitting_runtime_s`、`run_failures`。
- Cubic EOS增强：`eos.py` 输出 PR/SRK 的 `Z_roots`、`Z_vapor`、`Z_liquid`、`phi_v`、`phi_l`、`K=phi_l/phi_v`，并保留 Wilson fallback。
- 新增 `data/binary_interactions.json`：默认 `kij` 二元交互参数。
- Henry溶解度数据化：`solubility.py` 从 `data/solubility_parameters.json` 读取 Henry 参数，支持 solvent/catalyst_family 修正和实验校准入口。
- Recipe engine：新增 `recipe.py`，定义 `RecipeStep`、recipe JSON导入导出、事件日志，并把 quench、staged feed、H2策略映射到 ODE配置。
- 动态ODE增强：输出液相/气相组成、压力轨迹、夹套移热、控制器输出、C2/C3/ENB终点组成、recipe event log；quench事件使催化剂快速失活。
- 本地SQLite数据仓库：新增 `db.py`，表包括 `experiments`、`parameter_sets`、`cases`、`model_runs`、`reports`、`cfd_runs`。
- 模型可信度与不确定性：新增 `uncertainty.py`，支持 Monte Carlo / Latin Hypercube 扰动，输出 KPI P05/P50/P95、tornado proxy、风险概率。
- 长任务状态服务：新增 `services/task_service.py`，统一 `pending/running/success/failed/cached` 状态，用于参数估计、ODE、优化、Pareto、不确定性和报告导出。
- CFD/OpenFOAM增强：新增 boundary object；CFD字段含 `dead_zone_mask`、`high_fouling_mask`；VTK导出包含 masks；OpenFOAM case 增加 `0/C` 和 `system/controlDict.scalarTransportFoam`。
- 案例包增强：zip内新增 `manifest.json`，包含 `app_version`、`created_at`、`config_hash`、`parameter_set_id`、`data_snapshot_id`、`test_status`。
- 报告增强：Excel/Word/PDF支持 uncertainty、model confidence、recipe、task log、manifest。
- README强制更新：本文件记录版本差异、模块变化、核心技术参数、测试结果、局限性和下一版计划。

新增/修改模块：

- 新增：`epdm_sim/recipe.py`、`epdm_sim/db.py`、`epdm_sim/uncertainty.py`、`epdm_sim/services/task_service.py`、`epdm_sim/cfd/boundary.py`
- 新增数据：`data/binary_interactions.json`、`data/solubility_parameters.json`
- 修改：`parameter_estimation.py`、`eos.py`、`solubility.py`、`reactor.py`、`flowsheet.py`、`case_manager.py`、`report.py`、`app.py`、相关 Streamlit 页面、CFD导出和测试
- 废弃：无。旧的 empirical proxy、Wilson K、快速动态模型、JSON/CSV数据文件均保留为 fallback。

新增测试：

- `tests/test_recipe.py`
- `tests/test_db.py`
- `tests/test_uncertainty.py`
- `tests/test_task_service.py`
- `tests/test_v4_models.py`

本次验收结果：

```text
python -m py_compile app.py epdm_sim/**/*.py  -> passed
python -m pytest                              -> 69 passed
python scripts/smoke_app.py                   -> smoke ok
streamlit run app.py                          -> http://127.0.0.1:8501 returned HTTP 200
```

### V3 vs V2 摘要

- `app.py` 瘦身为入口/导航/session 初始化。
- 页面拆分到 `epdm_sim/pages/`，服务拆分到 `epdm_sim/services/`。
- 新增性能诊断、Henry溶解度、PR/SRK简化EOS、Pareto工艺窗口、案例zip包、CFD诊断、OpenFOAM pipe blockMesh skeleton、报告增强。

### V2 vs V1 摘要

- 从展示型数字孪生升级为数据校准型研发MVP。
- 新增催化剂知识库、实验数据管理、非线性参数估计、参数集版本管理、DOE建议、氢调实验设计、2L/5L放大、非牛顿流变、回收循环、热安全、案例管理和报告增强。

### V1 摘要

- 建立基础流程模拟：Feed、Mixer、Preheater、Reactor、Quench、Flash-1、Flash-2、Recycle、Product。
- 建立 Streamlit 中文界面、3D装置、CFD简化可视化、产品性能预测、Vistalon-like对标、敏感性和优化。

## 4. 安装与运行

```bash
cd D:\codex\metallocene-epdm-digital-twin
pip install -r requirements.txt
streamlit run app.py
```

基础依赖离线可运行。`thermo`、`chemicals`、`PyVista`、`FEniCSx/dolfinx`、`kaleido` 为可选增强；不可用时自动降级到内置模型或表格摘要。

## 5. 软件页面

- 数字孪生总览：3D装置总览、KPI、风险诊断、牌号匹配、Sankey。
- 釜式聚合工艺时序：快速动态模型、ODE详细模型、recipe编辑、event log。
- 反应器与动力学：液相浓度、气液传质、ENB竞争插入、氢调、催化剂失活。
- 热量衡算与流体性质：反应热、冷却、绝热温升、黏度、压降、泵功率、热安全。
- 分离脱挥与回收：Henry/EOS、Flash-1、Flash-2、回收循环。
- 产品性能与美孚对标：C2/C3/ENB、Mw/PDI/门尼、Tg/Tm、Vistalon-like窗口。
- 实验数据管理：CSV/Excel导入、标准化、质检、SQLite导入和查询。
- 参数集与非线性估计：参数集切换、proxy/flowsheet/ODE/hybrid拟合、残差、置信区间、相关性。
- 案例与场景管理：保存、加载、复制、对比、zip导入导出。
- CFD有限元可视化：速度、压力、温度、ENB、固含、黏度、壁面剪切、挂胶风险、VTK/OpenFOAM。
- 敏感性分析与优化：单变量扫描、单目标优化、Pareto窗口、不确定性分析。
- 3D装置库：原料罐、预热器、聚合釜、闪蒸罐、脱挥器、泵、压缩机、产品罐。
- 报告导出：Excel、Word、PDF。

## 6. 核心数据流

```text
用户输入 / 案例 / 参数集 / 实验数据
  -> SimulationState
  -> services/simulation_service.py
  -> flowsheet.py
  -> reactor / flash / heat_balance / fluid_props / polymer_props
  -> ResultsStore
  -> UI pages / report.py / case_manager.py / db.py
```

重计算策略：

- 快速 flowsheet 可自动复用 hash cache。
- ODE、CFD、优化、Pareto、参数估计、不确定性和报告导出必须按钮触发。
- `TaskService` 记录任务状态、耗时、参数hash、缓存命中和错误信息。

## 7. 核心模型公式

### 表观聚合动力学

```text
r_E   = k_E(T)   * C_E_liq   * Cstar
r_P   = k_P(T)   * C_P_liq   * Cstar
r_ENB = k_ENB_eff(T,P,C_E,C_ENB) * C_ENB_liq * Cstar

k_i(T) = k_i_ref * exp[-Ea_i/R * (1/T - 1/T_ref)]
Cstar = Ccat * f_AlTi * f_BHT * exp(-kd_h * tau_h)
f_AlTi = AlTi / (K_Al + AlTi)
f_BHT = 1 + alpha_BHT * BHT_ratio / (K_BHT + BHT_ratio)

pressure_factor_ENB = 1 / (1 + beta_P * max(P_MPa - 0.7, 0))
competition_factor = 1 / (1 + beta_E * C_E_liq / max(C_ENB_liq, tiny))
k_ENB_eff = k_ENB(T) * pressure_factor_ENB * competition_factor
```

### 氢调分子量

```text
chain_transfer_factor = 1 + ktr_H2 * C_H2_liq
Mw = Mw0 / chain_transfer_factor
Mn = Mw / PDI
```

### 反应热与移热

```text
Q_rxn_kJ_h = -(n_E*dH_E + n_P*dH_P + n_ENB*dH_ENB)
Q_rxn_kW = Q_rxn_kJ_h / 3600
deltaT_ad_K = Q_rxn_kJ_h / (mass_holdup_kg * Cp_mix_kJ_kgK)
Q_removed = U * A * LMTD
cooling_margin_kW = Q_max_kW - Q_rxn_kW
```

### 流体性质与压降

```text
rho_mix = total_mass / sum(m_i / rho_i)
Cp_mix = sum(w_i * Cp_i)
rho_gas = P * MW_mix / (R * T)
ln(mu_solvent_mix) = sum(x_i * ln(mu_i))
mu_solution = mu_solvent_mix * exp(A_mu*S + B_mu*S^2) * (Mw/300000)^alpha_Mw * exp(E_mu/R*(1/T - 1/T_ref))

Re = rho * v * D / mu
f = 64/Re                      (laminar)
f = 0.3164/Re^0.25              (turbulent)
DeltaP = f * (L/D) * rho*v^2/2
pump_power = DeltaP * volumetric_flow / efficiency
```

### Henry溶解度

```text
C_i_star = H_i_ref(solvent) * P_i * exp[-dH_solution/R * (1/T - 1/T_ref)] * solvent_factor * catalyst_family_factor
```

### Wilson K

```text
ln(K_i) = ln(Pc_i/P) + 5.373*(1+omega_i)*(1 - Tc_i/T)
```

### Cubic EOS PR/SRK

```text
PR:
a = 0.45724 * R^2 * Tc^2 / Pc * alpha
b = 0.07780 * R * Tc / Pc
Z^3 -(1-B)Z^2 +(A-3B^2-2B)Z -(AB-B^2-B^3)=0

SRK:
a = 0.42748 * R^2 * Tc^2 / Pc * alpha
b = 0.08664 * R * Tc / Pc
Z^3 - Z^2 + (A-B-B^2)Z - AB = 0

phi_v / phi_l from selected vapor/liquid Z roots
K = phi_l / phi_v, with Wilson fallback for single-root states
```

### 门尼、Tg、Tm和挂胶

```text
ln(ML) = a0 + a1*ln(Mw/100000) + a2*PDI + a3*C2_wt + a4*ENB_wt + a5*LCB_index
1/Tg = wE/Tg_E + wP/Tg_P + wD/Tg_ENB
Tm_est = 40 + 1.5*(C2_wt - 50) - 0.5*ENB_wt
fouling_index = solids_wt^2 * (Mw/300000)^0.8 * exp(1500/T) * wall_factor
```

### CFD风险场

```text
mu(x,y)=mu_solvent*exp(A_mu*S+B_mu*S^2)*(Mw/300000)^alpha*exp(E_mu/R*(1/T-1/Tref))
fouling_index(x,y)=normalized_viscosity*wall_proximity_factor*low_velocity_factor*high_polymer_factor*high_temperature_factor
dead_zone_mask = |u| < 0.05 * mean(|u|)
wall_shear = mu * |u| / wall_distance
```

## 8. 核心技术参数表

### default_config.yaml 主要工艺参数

| 参数 | 默认值 | 单位 | 说明 |
|---|---:|---|---|
| temperature_C | 100 | degC | 反应温度 |
| pressure_MPa | 1.0 | MPa | 反应压力 |
| reactor_volume_L | 5 | L | 聚合釜体积 |
| residence_time_min | 30 | min | 停留/批次代表时间 |
| solvent | hexane | - | 默认溶剂，可选 heptane/toluene |
| solvent_mass_kg_h | 100 | kg/h | 溶剂进料 |
| ethylene_kg_h | 20 | kg/h | 乙烯进料 |
| propylene_kg_h | 30 | kg/h | 丙烯进料 |
| enb_kg_h | 3 | kg/h | ENB进料 |
| hydrogen_g_h | 5 | g/h | 氢气链转移剂 |
| catalyst_umol_h | 100 | umol/h | 催化剂用量 |
| AlTi_ratio | 1000 | mol/mol | MAO Al/Ti |
| BHT_ratio | 0 | ratio | BHT调节比例 |
| reactor_mode | semi_batch | - | 默认半连续釜式 |
| num_cstr | 2 | - | 串联CSTR数量 |
| flash1_T_C / flash1_P_MPa | 80 / 0.2 | degC / MPa | 一级闪蒸 |
| flash2_T_C / flash2_P_MPa | 140 / 0.02 | degC / MPa | 二级脱挥 |
| purge_fraction | 0.05 | - | purge比例 |
| U_W_m2K / A_m2 | 300 / 2.0 | W/m2/K / m2 | 默认移热参数 |
| coolant_in_C / coolant_out_C | 25 / 35 | degC | 冷却介质温度 |
| pipe_length_m / pipe_diameter_m | 10 / 0.025 | m | 管路压降 |
| agitation_rpm | 500 | rpm | 搅拌转速 |
| impeller_type | pitched_blade | - | 默认斜叶桨 |
| baffles | true | - | 是否有挡板 |

### KineticParameters 默认值

| 参数 | 默认值 | 单位 | 适用范围 |
|---|---:|---|---|
| k_E_ref | 3.6e6 | L/mol/h proxy | 表观乙烯插入 |
| k_P_ref | 1.45e6 | L/mol/h proxy | 表观丙烯插入 |
| k_ENB_ref | 4.0e6 | L/mol/h proxy | 表观ENB插入 |
| Ea_E / Ea_P / Ea_ENB | 28000 / 32000 / 36000 | J/mol | Arrhenius温度修正 |
| kd_h | 0.08 | 1/h | 催化剂失活 |
| K_Al | 300 | Al/Ti ratio | MAO饱和常数 |
| K_BHT | 1.0 | ratio | BHT饱和常数 |
| alpha_BHT | 0.15 | - | BHT活性修正 |
| beta_P | 0.35 | 1/MPa | ENB压力惩罚 |
| beta_E | 0.01 | - | 乙烯竞争插入 |
| ktr_H2 | 45 | L/mol proxy | 氢调链转移 |
| Mw0 | 620000 | g/mol | 无氢基准Mw |
| dH_E / dH_P / dH_ENB | -95 / -85 / -80 | kJ/mol | 聚合热 |

### HeatBalance

| 参数 | 默认值 | 单位 | 说明 |
|---|---:|---|---|
| deltaH_ethylene | -95 | kJ/mol | 乙烯聚合热 |
| deltaH_propylene | -85 | kJ/mol | 丙烯聚合热 |
| deltaH_ENB | -80 | kJ/mol | ENB聚合热 |
| U | 300 | W/m2/K | 总传热系数 |
| A | 2.0 | m2 | 换热面积 |
| thermal risk | <5 low, 5-20 medium, >20 high | K | 按绝热温升分级 |
| cooling_margin | Q_max - Q_rxn | kW | 移热裕度 |

### FluidProperties / Rheology

| 参数 | 默认值 | 单位 | 说明 |
|---|---:|---|---|
| A_mu | 8 | - | 固含一次项 |
| B_mu | 15 | - | 固含二次项 |
| alpha_Mw | 0.6 | - | Mw指数 |
| E_mu | 12000 | J/mol | 黏度温度项 |
| T_ref | 373.15 | K | 黏度参考温度 |
| power_law_n | 0.72 | - | power-law指数 |
| carreau_lambda_s | 1.2 | s | Carreau时间常数 |
| pump_efficiency | 0.65 | - | 泵效率 |

### Solubility

| 组分/溶剂 | H_ref | 单位 | dH_solution J/mol | T_ref K |
|---|---:|---|---:|---:|
| ethylene/hexane | 0.18 | mol/L/MPa | -5500 | 373.15 |
| propylene/hexane | 0.24 | mol/L/MPa | -6500 | 373.15 |
| hydrogen/hexane | 0.015 | mol/L/MPa | -1200 | 373.15 |
| ethylene/heptane | 0.17 | mol/L/MPa | -5400 | 373.15 |
| propylene/heptane | 0.23 | mol/L/MPa | -6400 | 373.15 |
| hydrogen/heptane | 0.014 | mol/L/MPa | -1100 | 373.15 |
| ethylene/toluene | 0.15 | mol/L/MPa | -5200 | 373.15 |
| propylene/toluene | 0.20 | mol/L/MPa | -6100 | 373.15 |
| hydrogen/toluene | 0.011 | mol/L/MPa | -900 | 373.15 |

催化剂族修正：CGC-like 1.05、mono-metallocene-like 0.98、C3-3-TiMe2 1.03、D2-2-TiCl2 0.96。

### EOS / binary interactions

| pair | kij |
|---|---:|
| ethylene/hexane | 0.035 |
| propylene/hexane | 0.030 |
| hydrogen/hexane | 0.120 |
| ENB/hexane | 0.020 |
| ethylene/propylene | 0.010 |

`kij` 目前用于记录和后续混合规则扩展；V4的核心 K 输出为纯组分 PR/SRK fugacity root + Wilson fallback。

### CFD

| 参数 | 默认值 | 单位 | 说明 |
|---|---:|---|---|
| grid fast | 80 x 40 | cells | 默认快速CFD |
| pipe geometry | L=10, D=0.025 | m | 管道剖面 |
| reactor section | 5 L equivalent | - | 釜截面 |
| boundary names | inlet/outlet/walls/frontAndBack | - | 与OpenFOAM一致 |
| dead_zone | speed < 0.05 mean speed | - | 死区判据 |
| high_fouling_mask | fouling_index > 3 | - | 高挂胶区域 |
| wall_shear | mu*speed/wall_distance | Pa | 壁面剪切proxy |

### Optimizer / Pareto

目标：

- maximize grade match
- maximize ENB incorporation
- minimize ENB residue
- minimize fouling
- minimize heat duty
- maximize cooling margin
- minimize pressure drop

约束：

- `cooling_margin_kW > 0`
- `fouling_index < 3`
- pressure drop below limit
- solids below limit
- ENB residue below threshold

推荐窗口：稳健窗口、高ENB窗口、低风险窗口。

### Model registry / trigger policy

| 触发方式 | 用途 | 当前模块 |
|---|---|---|
| auto_cached | 页面切换和轻量参数查看时可复用缓存，避免重复计算 | flowsheet、thermo_flash、henry_solubility、reactor_kinetics、heat_balance、fluid_rheology_hydraulics、product_properties、conservation |
| button_manual | 需要用户明确点击运行，避免滑块触发重计算 | dynamic_semibatch_ode、parameter_estimation、cfd_simple、optimizer_pareto、uncertainty、engineering_rules、model_governance_v43 |
| data_only | 数据管理和审计，不直接触发模型求解 | data_case_report、model registry |
| export_only | 只在用户导出时生成文件 | openfoam_export、VTK/OpenFOAM case |

模型注册表字段：`module_id`、`display_name`、`category`、`origin_project`、`implementation`、`trigger_mode`、`equations`、`inputs`、`outputs`、`validity_range`、`engineering_logic`、`fallback`、`status`。

## 9. 数据文件说明

| 文件 | 用途 |
|---|---|
| `data/components.json` | 组分MW、Tc、Pc、omega、Cp、density、viscosity、thermal conductivity |
| `data/default_config.yaml` | 默认工艺条件 |
| `data/internal_experiments.csv` | 内置实验样品与组成/门尼/Mw数据 |
| `data/target_grades.json` | Vistalon-like和内部目标牌号 |
| `data/catalysts.json` | 催化剂知识库和PDF规则 |
| `data/fluid_property_calibration.csv` | 黏度/密度/Cp校准数据 |
| `data/parameter_sets.json` | 默认、PDF规则、用户校准参数集 |
| `data/binary_interactions.json` | Cubic EOS kij |
| `data/solubility_parameters.json` | Henry参数 |
| `data/engineering_rules.json` | V4.3化工趋势规则库 |
| `data/reaction_templates.json` | V4.3反应模板：EPDM默认模板和通用扩展模板 |
| `data/model_registry.json` | 合并后统一模型注册表：公式、输入/输出、适用范围、触发方式、fallback |
| `data/cases/` | 本地案例 |
| `data/epdm_digital_twin.sqlite` | V4本地SQLite数据仓库 |

## 10. 测试与验收

本次V4.3验收使用：

```text
python -m py_compile app.py epdm_sim/**/*.py scripts/**/*.py
python -m pytest
python scripts/smoke_app.py
```

结果：

```text
py_compile -> passed
pytest     -> 116 passed
smoke_app  -> smoke ok
```

建议发布前继续运行：

```bash
python scripts/smoke_app.py
streamlit run app.py
```

## 11. 报告导出

Excel包含：

- stream table
- unit operations
- reactor profile
- flash split
- heat balance
- fluid properties
- pressure drop
- engineering_checks
- conservation
- engineering_rules
- io_schema
- ui_actions
- ui_audit
- model_confidence_card
- reaction_templates
- model_contracts
- calibration
- DOE
- scaleup
- experiment_data
- data_quality
- parameter_sets
- parameter_estimation
- dynamic_semibatch
- case_comparison
- recycle_solver
- safety
- pareto_frontier
- uncertainty
- model_confidence
- recipe
- task_log
- manifest

Word/PDF包含：

- 输入条件
- 关键KPI
- 热量衡算
- 流体性质
- 压降与泵送
- 工程逻辑检查
- 守恒闭合
- 模型可信度
- 化工趋势规则摘要
- IO schema / UI点击路径摘要
- 模型适用范围与单位
- 3D装置与CFD摘要
- Vistalon-like对标
- 模型校准
- 非线性参数估计
- 动态釜式模拟
- 回收循环
- 热安全
- Pareto窗口
- 模型卡与不确定性
- Recipe与任务日志
- 案例manifest
- 模型假设和数据缺口

若 `kaleido` 不可用，图像导出自动降级为表格摘要，不报错。

## 12. 已知局限性

- 参数估计可调用真实 flowsheet/ODE，但内部实验数据字段仍有限，尤其缺少系统氢调、时间序列温度/压力/热流、真实气液组成和实时投料记录。
- PR/SRK EOS 已输出 Z/phi/K，但V4仍以纯组分 fugacity root 为主，混合物 fugacity和完整 kij mixing rule 仍需后续扩展。
- Henry参数为工程默认值，需要用 C2/C3/H2 在真实溶剂/胶液中的溶解度实验校准。
- 动态ODE已有 recipe/event/quench 入口，但压力控制、PID控制和气相headspace仍为简化工程形式。
- CFD仍为2D/准3D趋势模型，不包含真实桨叶几何、湍流模型、自由液面、非等温多相耦合和真实壁面沉积动力学。
- Vistalon-like对标仅为公开指标窗口风格的研发对标，不代表商业产品复刻。
- 不确定性分析为快速 Monte Carlo/LHS proxy，输入分布默认较粗，需要基于实验残差和参数协方差重新定义。
- SQLite为本地轻量仓库，尚未加入完整迁移系统和权限管理。

## 13. 下一版计划

V5建议：

- 完整混合物 PR/SRK fugacity coefficient，支持组成、kij矩阵、phi_i^v/phi_i^l和相稳定性判断。
- 实验时间序列对齐：温度、压力、气体补料、热流、扭矩/功率、取样组成。
- 参数估计增加 bootstrap/贝叶斯后验，形成可审计 parameter card。
- Recipe engine升级为事件驱动控制器，支持PID参数、阀门开度、压力控制补料和异常工况。
- CFD接入OpenFOAM case模板库和真实釜几何导入。
- 报告增加模型审计编号、数据版本、参数集签名、测试快照和一键case复现实验包。
- UI增加后台任务队列和异步进度，但仍保持本地无服务依赖。

