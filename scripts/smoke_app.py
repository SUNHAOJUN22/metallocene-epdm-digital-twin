"""Small offline smoke check for the EPDM digital twin app."""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app
from epdm_sim.flowsheet import load_default_config, run_flowsheet
from epdm_sim.report import export_excel, export_word_report


def main() -> None:
    """Import app, run a fast case and generate small report artifacts."""
    assert "数字孪生总览" in app.PAGES
    result = run_flowsheet(load_default_config())
    out = Path("tmp_smoke_outputs")
    out.mkdir(exist_ok=True)
    (out / "smoke.xlsx").write_bytes(export_excel(result))
    (out / "smoke.docx").write_bytes(export_word_report(result))
    print("smoke ok", result.kpis["polymer_kg_h"])


if __name__ == "__main__":
    main()
