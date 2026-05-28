# Testing Changelog

## V6.4

- Added nonlinear residual loop and solve-path integrator audit artifacts for equation-oriented flowsheet closure.
- Added industrial data package, benchmark reconciliation, property runtime audit and governance certificate outputs.
- Added adaptive integrator, event localization and residual decision engine report/repro tables.
- Release gate now checks V6.4 markdown changelog presence and V6.4 registry/benchmark versions.

## V6.3

- Added equation-oriented conservation solver, conservation Jacobian, data assimilation and calibration data package audit artifacts.
- Added property runtime context, adaptive step control, dynamic event detection, residual-aware sampling and model confidence certificate tables.
- Release gate now checks V6.3 markdown changelog presence and V6.3 registry/benchmark versions.

## V6.2

- Added conservation solve path, property model runtime, dynamic solver policy and step-acceptance audit sheets.
- Added residual-aware optimizer/DOE helpers and evidence-chain score/gap-priority artifacts.
- Release gate now checks V6.2 markdown changelog presence and V6.2 registry/benchmark versions.

## V6.1

- Added conservation correction certificates, calibrated property bridge and dynamic solver decision audit sheets.
- Added residual-aware posterior/uncertainty/DOE decision helpers and evidence-chain governance.
- Release gate now checks V6.1 markdown changelog presence and V6.1 registry/benchmark versions.

## V6.0

- Added industrial math-core traceability graphs linking equations, residuals and data lineage.
- Added constrained solver certificates, DAE/state invariant diagnostics and evidence-weighted confidence.
- Added calibrated property model selector and V6.0 report/repro industrial audit sheets.
- Release gate now checks markdown changelog presence and V6.0 registry/benchmark versions.

## V5.4

- Added unit-safe model-entry gates and unit conversion trace reporting.
- Added residual objective scoring for optimizer/DOE/window filtering.
- Added dynamic residual diagnostics, phase-equilibrium constraints and experimental benchmark metadata gates.
- Reports and repro packages now include V5.4 residual-aware optimization/DOE and benchmark snapshots.

## V5.5

- Added residual solver and correction-trace gates.
- Added RHS-residual coupling checks for dynamic template ODE profiles.
- Added benchmark calibration scoring and benchmark data-gap recommendations.
- Began API-compatible math-core splitting into estimation/reactor/flowsheet/dynamic/fluid helper packages.

## V5.7

- Added equation-residual-code coupling checks and residual-acceptance policy tables.
- Added dynamic proof-style stability checks and benchmark source registry.
- Added calibrated property usage selector and V5.7 report/repro audit sheets.
- Added math_core/solver_core helper layers for future API-compatible module splitting.

## V5.6

- Added data-lineage records for benchmark and calibration datasets.
- Added residual-constrained fitting objective and acceptance tables.
- Added posterior residual filter and dynamic residual feedback diagnostics.
- Added equation reverse checks from implementation output back to registry metadata.
- Added calibrated property-model provenance and report/repro lineage artifacts.

## V5.3

- Added full-chain dimensioned input adapters and V5.3 math-kernel tests.
- ResidualSystem critical failures now gate DOE/window recommendations and audit scoring.
- Equation bindings include residual ids; reports/repro packages include residual and benchmark snapshots.

## V5.2

- Added DimensionedValue unit/quantity safety tests.
- Added residual-system, equation-binding, ODE-diagnostics, transport-core and parameter-constraint gates.
- Scientific benchmarks now include residual-system acceptance and V5.2 benchmark versions.

## V5.1

- Added validity-envelope checks, report consistency checks and performance-profile artifacts.
- Raised direct callable coverage release-gate threshold to >=450 references.
- Scientific benchmarks now include model version, equation id, units, tolerance, validity range and source rationale.

## V5.0

- Added unified Makefile/script entrypoints.
- Added function matrix documentation generation.
- Added continued direct callable coverage tests.
- Release gate remains the authoritative quality gate.
