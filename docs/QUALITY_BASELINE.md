# Quality Baseline

## Latest Automated Results

| gate | passed | detail |
| --- | --- | --- |
| module_import | True | 262/262 modules imported |
| callable_direct_reference | True | 1021/1021 public callables directly referenced |
| function_matrix | True | 1021 callable rows with UI/API/DB/file/science risk tags |

## Release Gate

| gate | passed | runtime_s |
| --- | --- | --- |
| py_compile | True | 0.4958337000000483 |
| pytest | True | 58.77638450000006 |
| smoke_app | True | 6.160452200000009 |
| auto_functional_audit | True | 10.86963789999993 |
| function_inventory_audit | True | 4.151212299999997 |
| performance_profile | True | 5.949203099999977 |
| ui_e2e_smoke | True | 5.308278599999994 |
| ui_e2e_workflow | True | 4.914122299999917 |
| static_contracts | True | 0.0303354000000126 |

## Baseline Policy

- `make quality-gate` is the authoritative local release check.
- New scientific formulas require a golden or equation-code consistency test.
- New exported figures require plot validation metadata.
- New external-simulator exchange paths must stay offline/dry-run by default, preserve explicit units, avoid report-time heavy execution and keep ResidualSystem/release_gate as the acceptance authority.
- Aspen Plus/HYSYS artifacts are covered by report required-sheet checks, professional-skill Excel QA and direct tests for export, import validation, reconciliation and MCP dry-run behavior.
