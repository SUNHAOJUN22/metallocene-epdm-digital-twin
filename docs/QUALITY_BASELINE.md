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
| py_compile | True | 1.2386667000027956 |
| pytest | True | 106.33063259999837 |
| smoke_app | True | 9.485388299999611 |
| auto_functional_audit | True | 22.29158019999886 |
| function_inventory_audit | True | 4.414141299999756 |
| performance_profile | True | 6.389532199998939 |
| ui_e2e_smoke | True | 3.0336343000017223 |
| ui_e2e_workflow | True | 2.7805612000011024 |
| static_contracts | True | 0.0241516999994928 |

## Baseline Policy

- `make quality-gate` is the authoritative local release check.
- New scientific formulas require a golden or equation-code consistency test.
- New exported figures require plot validation metadata.
