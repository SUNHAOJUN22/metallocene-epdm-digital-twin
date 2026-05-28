# Quality Gates

The canonical gate is `make quality-gate`, implemented by `scripts/release_gate.py`.

Gate order:

1. Python compile.
2. Pytest.
3. Smoke app.
4. Auto functional audit.
5. Function inventory audit.
6. UI E2E smoke.
7. UI workflow smoke.
8. Static artifact/version contract.
