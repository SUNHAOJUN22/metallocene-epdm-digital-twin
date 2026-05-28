"""Recipe engine for dynamic semi-batch EPDM polymerization."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

try:
    from pydantic import BaseModel, Field
except Exception:  # pragma: no cover
    BaseModel = object  # type: ignore
    Field = lambda default_factory=None, default=None, **_: default if default_factory is None else default_factory()  # type: ignore


class RecipeStep(BaseModel):
    """One time-bounded operating step in a semi-batch recipe."""

    name: str
    start_min: float
    end_min: float
    feed_changes: dict[str, float] = Field(default_factory=dict)
    setpoints: dict[str, float] = Field(default_factory=dict)
    events: list[str] = Field(default_factory=list)


@dataclass
class Recipe:
    """Serializable recipe composed of ordered RecipeStep records."""

    recipe_id: str = "default_semibatch_recipe"
    description: str = "Default EPDM semi-batch recipe with staged activation and quench."
    steps: list[RecipeStep] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-serializable recipe payload."""
        return {
            "recipe_id": self.recipe_id,
            "description": self.description,
            "steps": [step.model_dump() if hasattr(step, "model_dump") else step.dict() for step in self.steps],
        }

    def to_json(self) -> str:
        """Serialize recipe to UTF-8 JSON text."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


def default_semibatch_recipe(total_time_min: float = 60.0) -> Recipe:
    """Return a default staged recipe consistent with the UI polymerization timeline."""
    t = max(float(total_time_min), 1.0)
    raw = [
        ("惰化", 0.00, 0.05, {}, {"nitrogen_blanket": 1.0}, ["inert_start"]),
        ("加溶剂/ENB", 0.05, 0.18, {"solvent": 1.0, "ENB": 1.0}, {"T_C": 35.0}, []),
        ("升温/充压", 0.18, 0.32, {"ethylene": 0.25, "propylene": 0.25, "hydrogen": 0.10}, {"pressure_MPa": 1.0, "T_C": 100.0}, []),
        ("催化剂注入", 0.32, 0.36, {"catalyst": 1.0, "MAO": 1.0, "BHT": 1.0}, {"T_C": 100.0}, ["catalyst_on"]),
        ("半连续聚合", 0.36, 0.84, {"ethylene": 0.70, "propylene": 0.70}, {"pressure_control": 1.0, "T_C": 100.0}, []),
        ("分段ENB微调", 0.50, 0.62, {"ENB": 0.25}, {"T_C": 100.0}, []),
        ("终止", 0.86, 0.90, {"quench": 1.0}, {"catalyst_active": 0.0}, ["quench"]),
        ("出料/闪蒸", 0.90, 1.00, {}, {"pressure_MPa": 0.2}, ["discharge"]),
    ]
    return Recipe(
        steps=[
            RecipeStep(
                name=name,
                start_min=start * t,
                end_min=end * t,
                feed_changes=feed,
                setpoints=setpoints,
                events=events,
            )
            for name, start, end, feed, setpoints, events in raw
        ]
    )


def recipe_from_dict(payload: dict[str, Any]) -> Recipe:
    """Build a Recipe from JSON-like dict data."""
    steps = [RecipeStep(**step) for step in payload.get("steps", [])]
    return Recipe(recipe_id=payload.get("recipe_id", "imported_recipe"), description=payload.get("description", ""), steps=steps)


def recipe_from_json(text: str) -> Recipe:
    """Load a recipe from JSON text."""
    return recipe_from_dict(json.loads(text))


def recipe_to_dataframe(recipe: Recipe) -> pd.DataFrame:
    """Return recipe steps as a UI-editable DataFrame."""
    rows = []
    for step in recipe.steps:
        payload = step.model_dump() if hasattr(step, "model_dump") else step.dict()
        rows.append(
            {
                "name": payload["name"],
                "start_min": payload["start_min"],
                "end_min": payload["end_min"],
                "feed_changes": json.dumps(payload.get("feed_changes", {}), ensure_ascii=False),
                "setpoints": json.dumps(payload.get("setpoints", {}), ensure_ascii=False),
                "events": ",".join(payload.get("events", [])),
            }
        )
    return pd.DataFrame(rows)


def recipe_from_dataframe(df: pd.DataFrame, recipe_id: str = "ui_recipe") -> Recipe:
    """Build a Recipe from an edited DataFrame."""
    steps: list[RecipeStep] = []
    for _, row in df.iterrows():
        try:
            feed_changes = json.loads(row.get("feed_changes", "{}") or "{}")
        except Exception:
            feed_changes = {}
        try:
            setpoints = json.loads(row.get("setpoints", "{}") or "{}")
        except Exception:
            setpoints = {}
        events = [item.strip() for item in str(row.get("events", "")).split(",") if item.strip()]
        steps.append(
            RecipeStep(
                name=str(row.get("name", "step")),
                start_min=float(row.get("start_min", 0.0)),
                end_min=float(row.get("end_min", 0.0)),
                feed_changes=feed_changes,
                setpoints=setpoints,
                events=events,
            )
        )
    return Recipe(recipe_id=recipe_id, description="Recipe edited in Streamlit UI.", steps=sorted(steps, key=lambda step: step.start_min))


def recipe_event_log(recipe: Recipe) -> pd.DataFrame:
    """Return all recipe events as a chronological table."""
    rows = []
    for step in recipe.steps:
        payload = step.model_dump() if hasattr(step, "model_dump") else step.dict()
        for event in payload.get("events", []):
            rows.append({"time_min": payload["start_min"], "step": payload["name"], "event": event})
        if payload.get("feed_changes"):
            rows.append({"time_min": payload["start_min"], "step": payload["name"], "event": "feed_change"})
    return pd.DataFrame(rows).sort_values("time_min").reset_index(drop=True) if rows else pd.DataFrame(columns=["time_min", "step", "event"])


def recipe_to_ode_config(recipe: Recipe, *, total_time_min: float, rpm: float, enb_strategy: str = "一次加入") -> dict[str, Any]:
    """Map a recipe to the existing ODE config dictionary."""
    event_log = recipe_event_log(recipe)
    has_quench = bool((event_log["event"] == "quench").any()) if not event_log.empty else False
    continuous_h2 = any("hydrogen" in (step.feed_changes or {}) and step.start_min > 0.2 * total_time_min for step in recipe.steps)
    staged_cat = sum(1 for step in recipe.steps if "catalyst" in (step.feed_changes or {})) > 1
    return {
        "total_time_min": total_time_min,
        "rpm": rpm,
        "enb_feed_strategy": enb_strategy,
        "hydrogen_feed_strategy": "连续补入" if continuous_h2 else "初始加入",
        "catalyst_feed_strategy": "分段注入" if staged_cat else "一次注入",
        "quench_active": has_quench,
        "recipe_event_log": event_log.to_dict(orient="records"),
    }
