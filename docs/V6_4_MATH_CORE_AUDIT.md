# V6.4 Math Core Audit

## Scope

This audit covers the V6.3 baseline and the V6.4 upgrade target: nonlinear residual-loop integration, industrial data packages, benchmark reconciliation, property runtime audit, adaptive integrator/event localization, residual-aware decision engine and model-governance UI data paths.

## Findings

1. Equation-oriented solving is currently an auditable bounded residual solve/certificate layer. V6.4 adds a nonlinear residual-loop dataframe and solve-path integrator, but full replacement of all recycle/flash/heat-balance nonlinear loops remains a V6.5 target.
2. Recycle, flash, heat-balance and flowsheet residuals are already represented in `ResidualSystem`, conservation solve certificates and equation-oriented solver rows. Some physical solve loops remain legacy-first and are now audited by `solve_path_integrator`.
3. Dynamic adaptive step control was diagnostic in V6.3. V6.4 adds adaptive integrator and event localization tables with rejected-step/event evidence, while full DAE event localization remains a future enhancement.
4. Calibrated property models affect Henry, viscosity, flash-K and deltaH runtime paths when enabled and valid. V6.4 adds property runtime audit rows to confirm residual safety and provenance.
5. Residual-aware optimizer, DOE and posterior paths existed separately. V6.4 adds a unified decision engine with explicit rejected reasons and bounded uncertainty risk.
6. Benchmark evidence still depends on local JSON/CSV metadata. V6.4 adds industrial package schema validation and benchmark reconciliation, but plant/LIMS/ELN ingestion remains future work.
7. Report/repro exports already include V6.3 lineage and confidence artifacts. V6.4 adds nonlinear loop, solve-path, industrial data, benchmark reconciliation, property audit, adaptive integrator, event localization, decision-engine and governance-certificate artifacts.
8. Large modules still worth API-compatible splitting include `flowsheet.py`, `reactor.py`, `parameter_estimation.py`, `dynamic_template_reactor.py`, `fluid_props.py`, `cfd/simple_solver.py` and `reporting/excel.py`.

## V6.5 Priorities

1. Replace more legacy recycle/flash/heat-balance iteration paths with equation-oriented residual systems and bounded physical projection.
2. Connect industrial data packages to LIMS/ELN/plant historian exports.
3. Promote adaptive integrator diagnostics into real time-step rejection and DAE algebraic constraint projection.
4. Surface governance certificate summaries in a richer model-governance dashboard with historical release-gate trend snapshots.

