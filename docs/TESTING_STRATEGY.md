# Testing Strategy

## Test Layers

1. Syntax/build: `make test-build`.
2. Unit/regression: `make test-unit`.
3. Scientific validation: `make test-science` and `make test-units`.
4. Integration: `make test-integration`.
5. UI contract smoke: `make test-e2e`.
6. Security/file safety: `make test-security`.
7. Release gate: `make quality-gate`.

## Rules

- Every repair must add or update a regression test.
- Scientific tests must assert finite, bounded and physically meaningful outputs.
- UI tests must not trigger heavy ODE/CFD/optimizer/posterior/DOE jobs unless explicitly requested.
