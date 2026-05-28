# V6.0 Math Core Audit

This audit covers the upgrade from V5.7 / 0.6.7 to V6.0 / 0.7.0.  The focus is industrial math-core governance: equation graph, residual graph, data-lineage graph, constrained solver certificates, DAE/state invariants, evidence-weighted model confidence and calibrated property model selection.

## 1. Screening-Level Models

The thermodynamics, flash, rheology, heat-balance and CFD layers remain R&D screening models.  V6.0 does not claim industrial design fidelity.  It adds audit certificates and evidence weighting so low-confidence default estimates are visible and can be replaced by calibrated property models.

## 2. Equations Without Deep Residual Coupling

V5.7 required each registered equation to expose a residual id.  V6.0 adds equation/residual/data lineage graph tables.  Some residual ids remain governance proxies rather than first-principles per-term residual equations, especially for grade score, Fox Tg and fouling index.  These should receive deeper physical residuals in V6.1.

## 3. Residual Feedback Coverage

ResidualSystem already gates optimizer/DOE/posterior helper paths.  V6.0 adds constrained solver certificates and residual graph outputs.  Remaining gap: every internal optimizer objective evaluation should call residual acceptance directly, instead of relying on wrapper/gate paths.

## 4. Benchmark Source Quality

Benchmark records distinguish plant, experiment, literature, synthetic and regression_snapshot.  V6.0 links benchmark ids to source/data-lineage tables, but several golden benchmark links are still registry-derived fallback records.  V6.1 should ingest reviewed raw VLE, calorimetry, rheology, GPC/Mooney, flash recovery and dynamic T/P profiles.

## 5. Dynamic ODE / DAE Invariants

V6.0 adds DAE-style state constraints and state invariant checks for dynamic profiles: nonnegative inventories, positive T/P, nondecreasing polymer/segment mass and residual feedback.  This is a proof-style diagnostic layer, not a full index-1 DAE solver.

## 6. Parameter Estimation Risks

Residual constrained fitting and posterior residual filters are present.  Remaining risk is that legacy parameter estimation entry points still expose empirical proxy modes.  Those should be wrapped more tightly with residual acceptance and calibrated parameter-set persistence in V6.1.

## 7. Report / Repro Consistency

Excel and repro packages now include model traceability, equation/residual/data-lineage graphs, solver certificates, validation evidence, confidence decomposition and property model selection.  Exports remain read-only and do not trigger ODE/CFD/optimizer/posterior/DOE tasks.

## 8. Large Modules

The main large API-compatible modules remain `parameter_estimation.py`, `reactor.py`, `flowsheet.py`, `dynamic_template_reactor.py`, `fluid_props.py` and `cfd/simple_solver.py`.  V6.0 continues the additive split into core helper modules while preserving old imports.

## 9. V6.1 Priorities

1. Integrate constrained solver certificates into every optimizer/DOE/posterior objective evaluation.
2. Add reviewed plant/experiment benchmark ingestion and source-review workflow.
3. Connect property model selector to solubility, flash, rheology and heat-balance runtime parameter selection.
4. Move DAE/state invariant diagnostics into dynamic solver adaptive fallback decisions.
5. Replace remaining governance-proxy residuals with equation-specific physical residual equations.
