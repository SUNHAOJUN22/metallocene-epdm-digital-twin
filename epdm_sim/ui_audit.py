"""Static UI workflow audit helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .utils import ROOT_DIR


HEAVY_FUNCTIONS = (
    "simulate_dynamic_semibatch_ode",
    "run_simple_cfd",
    "optimize_for_grade",
    "generate_pareto",
    "estimate_parameters",
    "export_excel",
    "export_word_report",
    "export_pdf_report",
)


@dataclass(frozen=True)
class UIAuditResult:
    """One UI/static-code audit item."""

    file: str
    issue_type: str
    severity: str
    message: str
    suggested_fix: str

    def as_dict(self) -> dict[str, Any]:
        """Return a DataFrame-friendly dictionary."""
        return self.__dict__.copy()


def _project_files(root: Path) -> list[Path]:
    """Return app/page files that participate in Streamlit navigation."""
    files = [root / "app.py"]
    pages_dir = root / "epdm_sim" / "pages"
    if pages_dir.exists():
        files.extend(sorted(pages_dir.glob("*.py")))
    return [path for path in files if path.exists()]


def _guarded(lines: list[str], index: int) -> bool:
    """Return whether a heavy call appears inside an explicit UI/task guard."""
    window = "\n".join(lines[max(0, index - 12) : index + 1])
    guard_tokens = ("st.button", "download_button", "TaskService", ".run(", "with st.spinner", "if run_", "if st.session_state")
    return any(token in window for token in guard_tokens)


def audit_file(path: Path) -> list[UIAuditResult]:
    """Audit one Python UI file for accidental heavy work on page load."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    issues: list[UIAuditResult] = []
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("from ") or stripped.startswith("import "):
            continue
        for fn in HEAVY_FUNCTIONS:
            if f"{fn}(" in stripped and not _guarded(lines, idx):
                issues.append(
                    UIAuditResult(
                        file=str(path),
                        issue_type="heavy_call_without_explicit_guard",
                        severity="warning",
                        message=f"{fn} appears outside an obvious button/TaskService guard at line {idx + 1}.",
                        suggested_fix="Wrap heavy computation in st.button and TaskService.run, or move it to a service function.",
                    )
                )
    if path.name == "app.py" and len(lines) > 260:
        issues.append(
            UIAuditResult(
                file=str(path),
                issue_type="app_entry_too_large",
                severity="warning",
                message=f"app.py has {len(lines)} lines; keep it as a thin entry point.",
                suggested_fix="Move page logic into epdm_sim/pages and service logic into epdm_sim/services.",
            )
        )
    if path.name != "__init__.py" and "st.error" not in text and "safe_render" not in text and "try:" not in text:
        issues.append(
            UIAuditResult(
                file=str(path),
                issue_type="missing_engineering_error_path",
                severity="info",
                message="No explicit engineered error-display path was detected.",
                suggested_fix="Use st.error/st.warning around user-triggered work where failures are plausible.",
            )
        )
    return issues


def run_ui_audit(root: str | Path | None = None) -> list[UIAuditResult]:
    """Run the lightweight static UI audit."""
    project_root = Path(root) if root is not None else ROOT_DIR
    issues: list[UIAuditResult] = []
    for path in _project_files(project_root):
        issues.extend(audit_file(path))
    return issues


def ui_audit_dataframe(results: list[UIAuditResult] | None = None) -> pd.DataFrame:
    """Return audit results as a DataFrame."""
    results = run_ui_audit() if results is None else results
    return pd.DataFrame([result.as_dict() for result in results])
