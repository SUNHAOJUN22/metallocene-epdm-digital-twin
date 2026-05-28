# Quality Baseline

## Latest Automated Results

| gate | passed | detail |
| --- | --- | --- |
| module_import | True | 261/261 modules imported |
| callable_direct_reference | True | 1007/1007 public callables directly referenced |
| function_matrix | True | 1007 callable rows with UI/API/DB/file/science risk tags |

## Release Gate

| gate | passed | runtime_s |
| --- | --- | --- |
| py_compile | True | 0.4786588000024494 |
| pytest | True | 81.66285540000172 |
| smoke_app | True | 8.985680100002355 |
| auto_functional_audit | True | 22.189002499999333 |
| function_inventory_audit | True | 3.374868899998546 |
| performance_profile | True | 6.131317999999737 |
| ui_e2e_smoke | True | 4.583414699998684 |
| ui_e2e_workflow | True | 4.579738200001884 |
| static_contracts | True | 0.0465841000004729 |

## Baseline Policy

- `make quality-gate` is the authoritative local release check.
- `make professional-skill-qa` is the executable peripheral QA command for professional skill replacement coverage: Excel workbook QA, Word report QA, UI artifact QA, GitHub workflow readiness and MCP interface contract QA.
- New scientific formulas require a golden or equation-code consistency test.
- New exported figures require plot validation metadata.
- New external tool interfaces must default to dry-run, require explicit unit context and preserve ResidualSystem/release_gate as the source of scientific truth.
