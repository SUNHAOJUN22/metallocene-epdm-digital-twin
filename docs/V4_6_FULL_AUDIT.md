# V4.6 Full Audit

## 1. Dynamic Reactor Template Status

V4.5 kept the detailed dynamic reactor as an EPDM-oriented profile model.
V4.6 adds `dynamic_template_reactor.py` and `state_vector.py` so a reaction
template can define ordered liquid monomer moles, gas moles, segment masses,
chain-transfer agents and scalar states.  The legacy EPDM columns remain for
compatibility.

## 2. Remaining EPDM Compatibility Fields

- `flowsheet.py` still produces C2/C3/ENB KPI aliases for the primary UI.
- Vistalon-like target grade matching is intentionally EPDM-specific.
- CFD scalar labels remain EPDM-focused, although V4.6 adds template-level
  dynamic and KPI adapters that can support generic templates.

## 3. Template Integration

- `kinetics.py`: template rates and conversions.
- `reactor.py`: template monomers, segment map and heats.
- `property_models.py`: template-dispatched polymer properties.
- `dynamic_template_reactor.py`: template-driven dynamic profile.
- `kpi_adapter.py`: template-aware KPI rows with EPDM compatibility aliases.

## 4. Validation and Governance

Preflight, conservation, engineering rules, model confidence and model audit
remain post/around-model checks.  V4.6 adds equation metadata, dimensional
checks, time-series profile residuals, Bayesian DOE, property confidence,
physical-constraint surrogate validation and reproducibility packages.

## 5. Heavy Task Trigger Risk

The UI action registry remains the canonical list of manual actions. V4.6 adds
actions for dynamic template ODE, time-series fitting, Bayesian DOE, surrogate
training/validation and reproducibility package export.  These are manual or
export actions and should not run on page load.

## 6. Mathematical Risk Points

- The dynamic template reactor uses a bounded explicit integrator for screening,
  not a rigorous stiff ODE solver.
- Bayesian DOE is a deterministic constrained ranking heuristic, not a full
  Bayesian posterior design solver.
- Surrogate models are local linear/ridge approximations and must remain inside
  their validity ranges.

## 7. Chemical Engineering Risk Points

- Henry, EOS and polymer-solution rheology still require experimental
  calibration for quantitative design.
- Generic templates are interface scaffolds. They are finite and conserved but
  not industrial models without data.
- Flash diagnostics enforce polymer nonvolatility and bounded splits but do not
  replace a full polymer-solution thermodynamic package.

## 8. Test Gaps Addressed

- State vector pack/unpack and non-negativity.
- Template dynamic reactor for EPDM and generic templates.
- Template-aware KPI rows.
- Equation registry and dimensional checks.
- Time-series import/alignment/residual scores.
- Bayesian DOE feasibility and weak-parameter scoring.
- Property confidence and audit contribution.
- Physical surrogate constraints and range warnings.
- Reproducibility package manifest roundtrip.

## 9. V4.7 Priority

1. Add real experimental time-series examples from instrument exports.
2. Replace the bounded explicit dynamic template integrator with optional
   `solve_ivp` stiff integration and event handling.
3. Extend CFD scalar labels to template monomers.
4. Add rigorous D-optimal design and Bayesian posterior updates when enough data
   exist.
5. Add a one-click validation suite that writes a signed model audit snapshot.
