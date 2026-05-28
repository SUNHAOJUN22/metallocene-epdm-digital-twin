from pathlib import Path

from epdm_sim.ui_audit import run_ui_audit, ui_audit_dataframe
from epdm_sim.utils import ROOT_DIR


def test_ui_audit_has_no_error_level_findings():
    results = run_ui_audit(ROOT_DIR)
    assert not [item for item in results if item.severity == "error"]
    df = ui_audit_dataframe(results)
    assert df is not None


def test_app_entry_remains_thin_enough():
    line_count = len((Path(ROOT_DIR) / "app.py").read_text(encoding="utf-8").splitlines())
    assert line_count <= 260


def test_all_page_files_importable():
    import importlib

    pages_dir = Path(ROOT_DIR) / "epdm_sim" / "pages"
    for path in pages_dir.glob("*.py"):
        if path.name == "__init__.py":
            continue
        importlib.import_module(f"epdm_sim.pages.{path.stem}")
