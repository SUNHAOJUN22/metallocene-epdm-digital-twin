"""High-level 3D digital twin views and equipment detail helpers."""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go

from .equipment_3d import (
    equipment_summary,
    feed_area_3d_figure,
    flash_vessel_3d_figure,
    heat_exchanger_3d_figure,
    product_tank_3d_figure,
    reactor_3d_figure,
)
from .layout_3d import EQUIPMENT_POSITIONS, process_3d_layout


VIEW_MODES = [
    "物料流模式",
    "热风险模式",
    "黏度/挂胶风险模式",
    "美孚对标模式",
    "CFD剖面模式",
]


def available_view_modes() -> list[str]:
    """Return UI labels for digital-twin view modes."""
    return VIEW_MODES.copy()


def selectable_equipment() -> list[str]:
    """Return equipment ids that can be highlighted in the 3D overview."""
    return ["总览"] + list(EQUIPMENT_POSITIONS.keys())


def build_digital_twin_figure(result=None, mode: str = "物料流模式", selected_equipment: str = "总览") -> go.Figure:
    """Build the main 3D digital-twin overview figure."""
    highlight = None if selected_equipment == "总览" else selected_equipment
    return process_3d_layout(result=result, mode=mode, highlight=highlight)


def equipment_detail_dataframe(result=None) -> pd.DataFrame:
    """Return a compact equipment table for the sidebar/detail panel."""
    return equipment_summary(result)


def figure_for_equipment(equipment: str, result=None, mode: str = "物料流模式") -> go.Figure:
    """Return a focused 3D sketch for an equipment family."""
    if equipment in {"Ethylene", "Propylene", "Hydrogen", "ENB", "Solvent", "CatalystSkid", "Feed"}:
        return feed_area_3d_figure()
    if equipment in {"Reactor1", "Reactor2", "Reactor", "CSTR"}:
        return reactor_3d_figure(result, mode=mode, highlighted=True)
    if equipment == "Flash1":
        return flash_vessel_3d_figure(result, flash="Flash-1")
    if equipment == "Flash2":
        return flash_vessel_3d_figure(result, flash="Flash-2 / Devolatilizer")
    if equipment in {"Preheater", "Condenser"}:
        return heat_exchanger_3d_figure(result)
    if equipment == "Product":
        return product_tank_3d_figure(result)
    return build_digital_twin_figure(result, mode=mode, selected_equipment=equipment)


def equipment_detail_text(equipment: str, result=None) -> dict[str, Any]:
    """Return key values shown next to a selected 3D equipment item."""
    k = getattr(result, "kpis", {}) if result is not None else {}
    detail = {
        "设备": equipment,
        "状态": "研发级估算",
        "聚合物产率 kg/h": k.get("polymer_kg_h"),
        "反应热 kW": k.get("heat_duty_kW"),
        "冷却裕度 kW": k.get("cooling_margin_kW"),
        "黏度 Pa.s": k.get("dynamic_viscosity_Pa_s"),
        "挂胶风险": k.get("fouling_risk"),
        "最佳对标牌号": k.get("best_grade"),
    }
    return {key: value for key, value in detail.items() if value is not None}
