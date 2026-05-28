# Quality Baseline

## Latest Automated Results

| gate | passed | detail |
| --- | --- | --- |
| module_import | True | 254/254 modules imported |
| callable_direct_reference | True | 972/972 public callables directly referenced |
| function_matrix | True | 972 callable rows with UI/API/DB/file/science risk tags |

## Release Gate

| gate | passed | runtime_s |
| --- | --- | --- |
| py_compile | True | 0.4497385000004215 |
| pytest | True | 49.36721829999988 |
| smoke_app | True | 4.913734800000384 |
| auto_functional_audit | True | 8.94578139999976 |
| function_inventory_audit | True | 2.9769821999998385 |
| performance_profile | True | 4.158322899999803 |
| ui_e2e_smoke | True | 4.186332900000707 |
| ui_e2e_workflow | True | 4.229506699999547 |
| static_contracts | True | 0.0386991000004854 |

## Baseline Policy

- `make quality-gate` is the authoritative local release check.
- New scientific formulas require a golden or equation-code consistency test.
- New exported figures require plot validation metadata.
- `make professional-skill-qa` is the executable peripheral QA command for workstreams that are suitable for professional skill replacement: Excel report QA, Word report QA, UI artifact QA and GitHub workflow readiness.
