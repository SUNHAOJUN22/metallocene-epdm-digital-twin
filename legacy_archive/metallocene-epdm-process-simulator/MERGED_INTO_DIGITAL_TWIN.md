# Merged into metallocene-epdm-digital-twin

This folder is now a compatibility and archival project inside the canonical
digital twin repository.

Canonical runtime:

```powershell
cd D:\codex\metallocene-epdm-digital-twin
streamlit run app.py
```

Compatibility behavior:

```powershell
cd D:\codex\metallocene-epdm-process-simulator
streamlit run app.py
```

The command above launches the canonical app from
`D:\codex\metallocene-epdm-digital-twin\app.py`.

Legacy audit entry:

```powershell
streamlit run legacy_app.py
```

Use `legacy_app.py` only for comparing the early MVP. New development, tests,
documentation and reports should be added to the parent
`metallocene-epdm-digital-twin` project.

Merge policy:

- `metallocene-epdm-digital-twin` is the only active product line.
- `metallocene-epdm-process-simulator` remains as source-history evidence under
  `legacy_archive/`.
- No legacy code is deleted; the original Streamlit app is preserved in
  `legacy_app.py`.
- Shared formulas and model assumptions are documented in the digital twin
  `data/model_registry.json` and `docs/MERGED_PROJECTS.md`.
