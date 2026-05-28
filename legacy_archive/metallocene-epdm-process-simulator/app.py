"""Compatibility launcher for the unified EPDM digital twin.

This project has been merged into ``metallocene-epdm-digital-twin``.  The
legacy Streamlit implementation is preserved as ``legacy_app.py`` for audit and
comparison, while ``streamlit run app.py`` now starts the canonical unified app.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


def _find_canonical_project() -> Path:
    """Find the merged digital-twin root from either old or archived location."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if parent.name == "metallocene-epdm-digital-twin" and (parent / "app.py").exists():
            return parent
        sibling = parent / "metallocene-epdm-digital-twin"
        if (sibling / "app.py").exists():
            return sibling
    raise FileNotFoundError("Cannot locate metallocene-epdm-digital-twin/app.py")


CANONICAL_PROJECT = _find_canonical_project()
CANONICAL_APP = CANONICAL_PROJECT / "app.py"


if not CANONICAL_APP.exists():
    raise FileNotFoundError(
        "Merged canonical project not found. Expected "
        f"{CANONICAL_APP}."
    )

sys.path.insert(0, str(CANONICAL_PROJECT))
runpy.run_path(str(CANONICAL_APP), run_name="__main__")
