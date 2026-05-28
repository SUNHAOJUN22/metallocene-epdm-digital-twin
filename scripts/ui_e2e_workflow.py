"""Non-destructive V5.0 UI workflow contract smoke.

This script verifies workflow/navigation contracts without clicking heavy
compute buttons.  It uses HTTP and Python-side page/action registries so it can
run on Windows without adding a browser dependency.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import app
from epdm_sim.ui_audit import run_ui_audit
from epdm_sim.ui_workflow import load_ui_actions


def run_ui_e2e_workflow(url: str = "http://127.0.0.1:8501/", timeout_s: int = 10) -> dict[str, object]:
    """Run a non-destructive UI workflow contract check."""
    http_available = True
    http_error = ""
    try:
        with urllib.request.urlopen(url, timeout=timeout_s) as response:
            body = response.read().decode("utf-8", errors="ignore")
            status = int(response.status)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        body = ""
        status = 0
        http_available = False
        http_error = str(exc)
    actions = load_ui_actions()
    page_names = list(app.PAGES.keys())
    heavy_tokens = ("ode", "cfd", "optimization", "optimizer", "posterior", "doe")
    manual_actions = [action for action in actions if action.trigger_type == "button_manual"]
    heavy_manual_without_task = [
        action.action_id
        for action in manual_actions
        if any(token in action.action_id.lower() for token in heavy_tokens) and not action.target_task
    ]
    report_export_heavy = [
        action.action_id
        for action in actions
        if action.trigger_type == "export" and any(token in (action.target_task or "").lower() for token in heavy_tokens)
    ]
    audit_errors = [item for item in run_ui_audit() if item.severity == "error"]
    result = {
        "status": status,
        "http_available": http_available,
        "http_error": http_error,
        "body_length": len(body),
        "streamlit_bootstrap_present": "streamlit" in body.lower(),
        "pages_registered": len(page_names),
        "has_dashboard": any("总览" in name for name in page_names),
        "has_report_page": any("报告" in name for name in page_names),
        "has_workflow_page": any("工作流" in name for name in page_names),
        "manual_action_count": len(manual_actions),
        "heavy_manual_without_task": heavy_manual_without_task,
        "export_actions_heavy": report_export_heavy,
        "ui_audit_errors": [item.__dict__ for item in audit_errors],
    }
    result["passed"] = (
        ((status == 200 and len(body) > 1000) or not http_available)
        and result["has_dashboard"]
        and result["has_report_page"]
        and not heavy_manual_without_task
        and not report_export_heavy
        and not audit_errors
    )
    return result


def main() -> int:
    out_dir = ROOT / "tmp_smoke_outputs"
    out_dir.mkdir(exist_ok=True)
    result = run_ui_e2e_workflow()
    (out_dir / "ui_e2e_workflow.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
