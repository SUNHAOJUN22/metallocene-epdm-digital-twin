# V5.6 Math Kernel Audit

This audit covers the V5.6 upgrade from V5.5 / 0.6.5 to V5.6 / 0.6.6.  The focus is experimental data lineage, residual-constrained calibration objectives, posterior residual acceptance, equation reverse checks, dynamic residual feedback and calibrated property-model provenance.

## 1. Benchmark Source Credibility

`data/experimental_benchmarks.json` contains `synthetic`, `literature`, `plant` and `regression_snapshot` records.  V5.6 adds `epdm_sim/data_lineage.py` so every benchmark can be converted into a lineage record with source type, source reference, unit, uncertainty, validity range, preprocessing steps and data hash.  Regression snapshots remain low-confidence and should not be treated as plant validation.

Remaining gap: raw plant/lab data are still placeholders or metadata records.  V5.7 should ingest measured VLE/flash recovery, reaction calorimetry, solution rheology, GPC/Mooney and dynamic T/P/Q profiles.

## 2. Residual-Constrained Parameter Estimation

V5.5 exposed `residual_aware_parameter_objective()`.  V5.6 adds `epdm_sim/estimation/residual_constrained_fit.py` with the explicit objective:

```text
objective = weighted_data_residual
          + lambda_mass * mass_residual_penalty
          + lambda_energy * energy_residual_penalty
          + lambda_phase * phase_residual_penalty
          + lambda_prior * parameter_prior_penalty
          + lambda_validity * extrapolation_penalty
```

The helper rejects target-unit mismatches, out-of-bound parameters and critical residual systems before a calibrated parameter set can be accepted.  It does not overwrite default parameter sets.

Remaining gap: this is an acceptance/objective layer.  The full nonlinear optimizer should call it internally in V5.7.

## 3. Posterior and Uncertainty Residual Acceptance

V5.6 adds `epdm_sim/posterior_residual_filter.py`.  Posterior samples are now annotatable with parameter-bound status, residual penalty, critical residual count and `residual_acceptance_rate`.  This closes the previous gap where posterior/uncertainty samples could be finite but not explicitly residual-accepted.

Remaining gap: posterior sampling still uses a lightweight R&D sampler.  Future work should combine residual acceptance with dataset likelihood and benchmark weights during sampling, not only as a post-filter.

## 4. Equation Registry Reverse Checks

V5.5 already bound registry equations to implementation functions.  V5.6 adds `epdm_sim/equation_reverse_check.py`, which starts from code bindings and checks that implementation functions, units, dimensional signatures, benchmark links and residual links remain present.

This is not a symbolic proof of every equation; it is an executable metadata and trend consistency gate.  Critical equation failures now surface in release gates.

## 5. Dynamic Residual Feedback

`dynamic_core/residual_timeseries.py` remains the profile-level residual table.  V5.6 adds `dynamic_core/residual_feedback.py` so residual severity is summarized into solver diagnostics:

- `residual_max_error`
- `residual_acceptance_rate`
- `critical_residual_count`
- `fallback_reason`
- `nfev`, `njev`, `step_count`

Remaining gap: step-level residual feedback is available to diagnostics, but the BDF/RK solver does not yet adapt step size or fallback purely from the residual table.

## 6. Calibrated Property Models

V5.6 adds `epdm_sim/calibrated_property_models.py` to store default or calibrated Henry/viscosity/flash-K/deltaH style models with:

- `dataset_id`
- `data_hash`
- `validity_range`
- `uncertainty`
- `source_type`
- confidence score

Default estimates remain low confidence.  Experiment/literature/plant calibrated records increase confidence and can be exported in reports/repro packages.

## 7. Report and Repro Lineage

Excel reports now include:

- `data_lineage`
- `residual_constrained_fit`
- `posterior_residual_filter`
- `equation_reverse_check`
- `dynamic_residual_feedback`
- `calibrated_property_models`

Repro packages now include:

- `data_lineage.csv`
- `calibrated_property_models.csv`
- `equation_reverse_check.csv`

Report export remains read-only and does not run ODE/CFD/optimizer/posterior/DOE tasks.

## 8. Remaining Large Modules

The following files still deserve staged decomposition, but are not blockers:

- `epdm_sim/parameter_estimation.py`
- `epdm_sim/reactor.py`
- `epdm_sim/flowsheet.py`
- `epdm_sim/dynamic_template_reactor.py`
- `epdm_sim/fluid_props.py`
- `epdm_sim/cfd/simple_solver.py`

## 9. V5.7 Priorities

1. Wire `residual_constrained_fit` into actual optimizer-based parameter estimation.
2. Add measured VLE, calorimetry, rheology, GPC/Mooney and dynamic T/P/Q benchmark datasets.
3. Make dynamic solver fallback decisions use residual feedback directly.
4. Connect calibrated property models into runtime Henry, flash, rheology and heat-balance parameter selection.
5. Add reviewer workflow for benchmark/data-lineage records.
