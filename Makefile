PYTHON ?= python

.PHONY: audit check-env lint typecheck test test-unit test-integration test-e2e test-science test-property test-fuzz test-regression test-security test-performance test-build coverage quality-gate validate benchmark report repair-common continuous-improve professional-skill-qa

audit:
	$(PYTHON) scripts/dev_tasks.py audit-project

check-env:
	$(PYTHON) scripts/dev_tasks.py check-env

lint:
	$(PYTHON) scripts/dev_tasks.py test-lint

typecheck:
	$(PYTHON) scripts/dev_tasks.py test-typecheck

test: test-unit

test-unit:
	$(PYTHON) scripts/dev_tasks.py test-unit

test-integration:
	$(PYTHON) scripts/dev_tasks.py test-integration

test-e2e:
	$(PYTHON) scripts/dev_tasks.py test-e2e

test-science:
	$(PYTHON) scripts/dev_tasks.py test-science

test-property:
	$(PYTHON) -m pytest -q tests/test_property_invariants.py

test-fuzz:
	$(PYTHON) -m pytest -q tests/test_file_security.py tests/test_preflight.py

test-regression:
	$(PYTHON) -m pytest -q tests/test_scientific_benchmarks.py tests/test_remaining_direct_coverage.py

test-units:
	$(PYTHON) scripts/dev_tasks.py test-units

test-security:
	$(PYTHON) scripts/dev_tasks.py test-security

test-performance:
	$(PYTHON) scripts/dev_tasks.py test-performance

test-build:
	$(PYTHON) scripts/dev_tasks.py test-build

coverage:
	$(PYTHON) -m pytest -q

quality-gate:
	$(PYTHON) scripts/dev_tasks.py quality-gate

validate: quality-gate

benchmark:
	$(PYTHON) scripts/dev_tasks.py benchmark

report:
	$(PYTHON) scripts/dev_tasks.py generate-test-report

repair-common:
	$(PYTHON) scripts/dev_tasks.py repair-common

continuous-improve:
	$(PYTHON) scripts/dev_tasks.py continuous-improve

professional-skill-qa:
	$(PYTHON) scripts/dev_tasks.py professional-skill-qa
