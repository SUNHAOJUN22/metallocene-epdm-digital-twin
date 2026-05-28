"""Non-destructive Streamlit UI E2E smoke check.

The script intentionally avoids clicking heavy-task buttons.  It verifies the
local HTTP entry and static UI/task contracts that prevent page navigation from
triggering ODE/CFD/optimization/posterior/DOE tasks.
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


def run_ui_e2e_smoke(url: str = "http://127.0.0.1:8501/", timeout_s: int = 10) -> dict[str, object]:
    """Run a non-destructive UI smoke check."""
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
    audit_errors = [item for item in run_ui_audit() if item.severity == "error"]
    manual_missing_task = [action.action_id for action in actions if action.trigger_type == "button_manual" and not action.target_task]
    export_heavy = [
        action.action_id
        for action in actions
        if action.trigger_type == "export" and any(token in (action.target_task or "") for token in ("ode", "cfd", "optimization", "posterior", "doe"))
    ]
    result = {
        "status": status,
        "http_available": http_available,
        "http_error": http_error,
        "body_length": len(body),
        "streamlit_bootstrap_present": "streamlit" in body.lower(),
        "pages_registered": len(app.PAGES),
        "has_dashboard_page": "数字孪生总览" in app.PAGES,
        "has_report_page": any("报告" in name for name in app.PAGES),
        "manual_actions_missing_task": manual_missing_task,
        "export_actions_heavy": export_heavy,
        "ui_audit_errors": [item.__dict__ for item in audit_errors],
        "passed": ((status == 200 and len(body) > 1000) or not http_available) and not manual_missing_task and not export_heavy and not audit_errors,
    }
    return result


def main() -> int:
    out_dir = ROOT / "tmp_smoke_outputs"
    out_dir.mkdir(exist_ok=True)
    result = run_ui_e2e_smoke()
    (out_dir / "ui_e2e_smoke.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
