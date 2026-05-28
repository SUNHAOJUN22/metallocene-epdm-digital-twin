"""Application state models for cached, modular simulation workflows."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field

from .utils import model_dump_compat


class SimulationState(BaseModel):
    """Single source of truth for user-facing simulation controls.

    The Streamlit UI keeps this model in ``st.session_state`` and passes only
    its ``config`` payload into the calculation engine. Heavy modules such as
    CFD, optimization and report generation are intentionally triggered on
    demand rather than recalculated by every widget rerender.
    """

    config: dict[str, Any]
    case_name: str = "基准案例 1109-2 commercial candidate"
    run_mode: str = "快速模式"
    theme: str = "深色"
    target_grade: str = "Internal_1109_2_commercial_candidate"
    dirty_modules: set[str] = Field(default_factory=lambda: {"flowsheet"})

    @classmethod
    def from_process_config(cls, config_model: Any, **kwargs: Any) -> "SimulationState":
        """Create state from a ProcessConfig-like Pydantic object."""
        return cls(config=model_dump_compat(config_model), **kwargs)

    def config_key(self) -> str:
        """Return a stable hashable JSON key for the current process config."""
        return json.dumps(self.config, sort_keys=True, ensure_ascii=False)

    def fingerprint(self) -> str:
        """Return a short content fingerprint for cache keys and diagnostics."""
        return hashlib.sha1(self.config_key().encode("utf-8")).hexdigest()[:12]

    def update_config(self, config_model: Any) -> None:
        """Replace the process config and mark downstream models dirty."""
        self.config = model_dump_compat(config_model)
        self.dirty_modules.update(
            {
                "flowsheet",
                "heat_balance",
                "fluid_props",
                "flash",
                "product",
                "3d",
            }
        )

    def mark_clean(self, *modules: str) -> None:
        """Mark modules as clean after successful calculation."""
        for module in modules:
            self.dirty_modules.discard(module)

    def mark_dirty(self, *modules: str, heavy: bool = False) -> None:
        """Mark modules as dirty after changing an input subset."""
        self.dirty_modules.update(modules or ("flowsheet",))
        if heavy:
            self.dirty_modules.update({"dynamic_reactor", "cfd", "sensitivity", "optimization", "report"})


@dataclass
class ResultsStore:
    """Lightweight in-session result cache for UI pages.

    ``flowsheet`` is reused across sidebar overview, dashboard, report preview
    and page panels during one rerun. Detail calculations keep their own keys
    so CFD and optimization never rerun unless explicitly requested.
    """

    flowsheet_key: str | None = None
    flowsheet: Any | None = None
    dynamic_key: str | None = None
    dynamic: Any | None = None
    cfd_key: str | None = None
    cfd: Any | None = None
    sensitivity: Any | None = None
    optimization: Any | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def invalidate_flowsheet(self) -> None:
        """Drop the fast flowsheet result while preserving manual detail runs."""
        self.flowsheet_key = None
        self.flowsheet = None

    def invalidate_detail(self) -> None:
        """Drop user-triggered heavy result objects."""
        self.dynamic_key = None
        self.dynamic = None
        self.cfd_key = None
        self.cfd = None
        self.sensitivity = None
        self.optimization = None
