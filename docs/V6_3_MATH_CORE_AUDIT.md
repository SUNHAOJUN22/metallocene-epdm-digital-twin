# V6.3 Math Core Audit

## Scope

This audit covers the V6.2 baseline and the V6.3 upgrade target: equation-oriented conservation solving, calibration data assimilation, property runtime context, adaptive dynamic step control, residual-aware sampling and model confidence certificates.

## Findings

1. Correction depth:
   - V6.2 conservation solve path is an auditable correction/acceptance layer. V6.3 adds a bounded equation-oriented residual table, finite-difference Jacobian and least-squares/Newton-style step certificate.
   - Full equation-oriented nonlinear flowsheet solving is still a V6.4 target.

2. Residual integration:
   - ResidualSystem already enters optimizer/DOE/posterior gates through residual-aware helpers.
   - V6.3 adds residual-aware sampling and confidence certificate tables so posterior/DOE/optimizer sampling decisions can be audited directly.

3. Calibrated property impact:
   - V6.2 property runtime can affect Henry, viscosity, flash-K and deltaH paths inside validity range.
   - V6.3 adds property runtime context, including residual acceptance status and calibrated/default runtime provenance.

4. Dynamic solver policy:
   - V6.2 records dynamic solver policy and step acceptance.
   - V6.3 adds adaptive step-control and event-detection tables for rejected-step, cooling-failure, quench and runaway diagnostics.

5. Benchmark evidence:
   - Current benchmark/source metadata are sufficient for automated gates.
   - Plant/experiment/literature coverage remains the main fidelity gap; many critical equations still rely on regression/synthetic evidence until more reviewed datasets are added.

6. Report/repro chain:
   - V6.3 report and repro package now include equation-oriented solver, conservation Jacobian, calibration package, data assimilation, property context, dynamic adaptive checks, residual-aware sampling and confidence certificate artifacts.

7. Large modules:
   - `parameter_estimation.py`, `reactor.py`, `flowsheet.py`, `dynamic_template_reactor.py`, `fluid_props.py`, `cfd/simple_solver.py` and `reporting/excel.py` remain large.
   - Continue API-compatible splitting only when behavior is covered by targeted tests.

## V6.4 Priorities

1. Connect equation-oriented residual solves deeper into recycle, flash and heat-balance iteration loops.
2. Add versioned plant historian / LIMS / ELN calibration data packages.
3. Move adaptive dynamic checks toward true step rejection and event localization.
4. Expose confidence certificates and evidence gaps in the UI governance dashboard.
