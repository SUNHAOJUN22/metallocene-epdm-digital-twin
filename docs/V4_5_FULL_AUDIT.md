# V4.5 Full Audit

## 1. Current Reaction Template Integration

V4.4 already connected `reaction_templates.json` to `reactor.py`,
`heat_balance.py` and `conservation.py`. V4.5 extends this by making
`kinetics.py` expose template-driven rate dictionaries and by adding
`property_models.py` for template-dispatched polymer properties.

## 2. Remaining EPDM-Specific Areas

- `flowsheet.py` still reports EPDM-compatible KPI names such as `C2_wt`,
  `C3_wt`, `ENB_wt`, `C2_conversion_pct`, `ENB_residue_ppm`.
- `dynamic_reactor.py` remains an EPDM-focused detailed stirred-tank model,
  although V4.5 provides a template-compatible direction and keeps old outputs.
- CFD fields still use ethylene/propylene/ENB scalar names.
- Vistalon-like grade matching is intentionally EPDM-specific.

## 3. Template Degree by Module

| Module | V4.5 status |
|---|---|
| `kinetics.py` | Template-aware `calculate_template_rates`, conversions and segment masses |
| `polymer_props.py` | Wrapper dispatches to `property_models.py` |
| `reactor.py` | Uses template monomers, segment map and deltaH while preserving EPDM outputs |
| `heat_balance.py` | Default deltaH comes from template |
| `conservation.py` | Segment balance can use template segment maps |

## 4. Calibration, DOE and Uncertainty Loop

`calibration_loop.py` links existing experiment coverage, identifiability,
uncertainty and DOE recommendation into a single lightweight loop. It does not
run ODE, CFD or optimizer unless a future UI explicitly asks for that heavy
workflow.

## 5. Preflight, Conservation and Engineering Rules Coverage

Preflight checks block invalid flowsheet/CFD/optimizer inputs before execution.
Conservation diagnostics explain where mass/energy closure issues are likely
located. Engineering rules continue to check expected chemical-engineering
trends such as H2-Mw, solids-viscosity and flash pressure-vapor fraction.

## 6. UI and Heavy Task Trigger Risk

The app uses page modules and a UI action registry. Heavy tasks should remain
button-triggered through `TaskService`. V4.5 adds a calibration-loop action and
keeps report export as an existing-results export path.

## 7. Mathematical Risk Points

- Generic templates are finite engineering proxies, not calibrated models.
- Parameter identifiability uses finite-difference/FIM proxies.
- DOE expected information gain is ranking logic, not a rigorous D-optimal
  experimental design solver.
- Dynamic reactor state names are still EPDM-oriented in exported profiles.

## 8. Chemical Engineering Risk Points

- Henry parameters, EOS binary interactions and viscosity parameters require
  experiments for quantitative design.
- Polymer solution non-Newtonian rheology is approximated with empirical,
  power-law and Carreau-Yasuda options.
- Flash behavior uses simplified K-value logic and sanity checks rather than
  a full polymer-solution thermodynamic package.

## 9. Test Gaps Closed in V4.5

- Template kinetics can run EPDM and generic templates.
- Property models can dispatch EPDM and generic templates.
- Calibration loop recommends targeted experiments for weak parameters.
- Rheology trends are tested for solids, temperature, Mw and shear thinning.
- Flash diagnostics check bounded vapor fraction and polymer nonvolatility.
- Model audit report checks score boundedness and calibration-score response.

## 10. V4.6 Priority

1. Generalize `dynamic_reactor.py` internal ODE state vectors by template.
2. Generalize flowsheet KPI names for non-EPDM templates.
3. Add real D-optimal or Bayesian experimental design with constraints.
4. Connect calibration-loop results to SQLite experiment/model-run snapshots.
5. Add template-specific CFD scalar labels and generic scalar transport names.
