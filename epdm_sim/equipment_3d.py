"""Plotly 3D equipment primitives and EPDM unit-operation sketches."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go


MATERIAL_COLORS = {
    "ethylene": "#7dd3fc",
    "propylene": "#22c55e",
    "ENB": "#f97316",
    "hydrogen": "#a78bfa",
    "solvent": "#d1b45f",
    "catalyst": "#ef4444",
    "polymer_solution": "#4338ca",
    "vapor_recycle": "#06b6d4",
    "product": "#1f2937",
    "steel": "#64748b",
    "coolant": "#38bdf8",
}

RISK_COLORS = {
    "normal": "#64748b",
    "thermal": "#f97316",
    "high": "#dc2626",
    "viscosity": "#7e22ce",
    "fouling": "#7f1d1d",
    "pressure": "#ef4444",
}


@dataclass(frozen=True)
class EquipmentDescriptor:
    """Small equipment metadata block used by hover text and reports."""

    equipment_id: str
    name_cn: str
    section: str
    x: float
    y: float
    z: float
    status: str = "normal"
    key_metric: str = ""


def _cylinder_mesh(
    center: tuple[float, float, float],
    radius: float,
    height: float,
    segments: int = 36,
    z0: float | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return surface arrays for a vertical cylinder."""
    theta = np.linspace(0.0, 2.0 * np.pi, segments)
    z_base = center[2] - height / 2.0 if z0 is None else z0
    z_vals = np.array([z_base, z_base + height])
    theta_grid, z_grid = np.meshgrid(theta, z_vals)
    x = center[0] + radius * np.cos(theta_grid)
    y = center[1] + radius * np.sin(theta_grid)
    return x, y, z_grid


def add_cylinder(
    fig: go.Figure,
    *,
    center: tuple[float, float, float],
    radius: float,
    height: float,
    name: str,
    color: str = "#64748b",
    opacity: float = 0.72,
    hover: str | None = None,
    showscale: bool = False,
) -> None:
    """Add a vertical cylinder shell to a 3D figure."""
    x, y, z = _cylinder_mesh(center, radius, height)
    fig.add_trace(
        go.Surface(
            x=x,
            y=y,
            z=z,
            name=name,
            surfacecolor=np.ones_like(z),
            colorscale=[[0, color], [1, color]],
            opacity=opacity,
            showscale=showscale,
            hovertemplate=hover or f"{name}<extra></extra>",
        )
    )
    # top and bottom rings make vessels easier to read without expensive caps
    theta = np.linspace(0.0, 2.0 * np.pi, 60)
    for zc in [center[2] - height / 2.0, center[2] + height / 2.0]:
        fig.add_trace(
            go.Scatter3d(
                x=center[0] + radius * np.cos(theta),
                y=center[1] + radius * np.sin(theta),
                z=np.full_like(theta, zc),
                mode="lines",
                line=dict(color="#334155", width=2),
                showlegend=False,
                hoverinfo="skip",
            )
        )


def add_box(
    fig: go.Figure,
    *,
    center: tuple[float, float, float],
    size: tuple[float, float, float],
    name: str,
    color: str = "#94a3b8",
    opacity: float = 0.72,
    hover: str | None = None,
) -> None:
    """Add a cuboid-like marker for compact process units."""
    fig.add_trace(
        go.Scatter3d(
            x=[center[0]],
            y=[center[1]],
            z=[center[2]],
            mode="markers+text",
            marker=dict(size=max(size) * 16, color=color, symbol="square", opacity=opacity),
            text=[name],
            textposition="top center",
            name=name,
            hovertemplate=hover or f"{name}<extra></extra>",
        )
    )


def add_pipe(
    fig: go.Figure,
    points: list[tuple[float, float, float]],
    *,
    name: str,
    color: str,
    width: int = 6,
    dash: str | None = None,
) -> None:
    """Add a colored material-transfer pipe/polyline."""
    fig.add_trace(
        go.Scatter3d(
            x=[p[0] for p in points],
            y=[p[1] for p in points],
            z=[p[2] for p in points],
            mode="lines",
            line=dict(color=color, width=width, dash=dash or "solid"),
            name=name,
            hovertemplate=f"{name}<extra></extra>",
        )
    )


def add_label(fig: go.Figure, text: str, point: tuple[float, float, float], color: str = "#0f172a") -> None:
    """Add a label at a process-equipment coordinate."""
    fig.add_trace(
        go.Scatter3d(
            x=[point[0]],
            y=[point[1]],
            z=[point[2]],
            mode="text",
            text=[text],
            textfont=dict(color=color, size=12),
            showlegend=False,
            hoverinfo="skip",
        )
    )


def risk_color_from_kpis(kpis: dict[str, Any], mode: str = "material") -> str:
    """Return a reactor shell color based on selected digital-twin layer."""
    if mode == "热风险模式":
        if kpis.get("cooling_margin_kW", 0.0) < 0 or kpis.get("thermal_risk") == "high":
            return RISK_COLORS["high"]
        if kpis.get("thermal_risk") == "medium":
            return RISK_COLORS["thermal"]
    if mode == "黏度/挂胶风险模式":
        if kpis.get("fouling_risk") == "high" or kpis.get("fouling_index", 0.0) >= 3.0:
            return RISK_COLORS["fouling"]
        if kpis.get("dynamic_viscosity_Pa_s", 0.0) > 0.01:
            return RISK_COLORS["viscosity"]
    return RISK_COLORS["normal"]


def reactor_3d_figure(result=None, mode: str = "黏度/挂胶风险模式", highlighted: bool = False) -> go.Figure:
    """Create a detailed stirred-tank reactor 3D sketch."""
    kpis = getattr(result, "kpis", {}) if result is not None else {}
    fig = go.Figure()
    shell_color = risk_color_from_kpis(kpis, mode)
    add_cylinder(
        fig,
        center=(0.0, 0.0, 1.4),
        radius=0.95,
        height=2.4,
        name="聚合反应器釜体",
        color=shell_color,
        opacity=0.54,
        hover=(
            "聚合反应器<br>"
            f"反应热: {kpis.get('heat_duty_kW', 0):.2f} kW<br>"
            f"固含: {kpis.get('solids_wt', 0):.2f} wt%<br>"
            f"挂胶风险: {kpis.get('fouling_risk', 'n/a')}<extra></extra>"
        ),
    )
    add_cylinder(fig, center=(0.0, 0.0, 1.4), radius=1.08, height=2.55, name="冷却夹套", color="#38bdf8", opacity=0.18)
    add_cylinder(fig, center=(0.0, 0.0, 0.9), radius=0.82, height=1.35, name="釜内胶液液位", color="#4338ca", opacity=0.35)
    add_cylinder(fig, center=(0.0, 0.0, 1.55), radius=0.07, height=2.2, name="搅拌轴", color="#111827", opacity=0.95)
    for z in [0.65, 1.15]:
        fig.add_trace(
            go.Scatter3d(
                x=[-0.58, 0.58, None, 0.0, 0.0],
                y=[0.0, 0.0, None, -0.58, 0.58],
                z=[z, z, None, z, z],
                mode="lines",
                line=dict(color="#111827", width=8),
                name="搅拌桨",
                hovertemplate="搅拌桨<extra></extra>",
                showlegend=False,
            )
        )
    for angle in np.linspace(0.0, 2.0 * np.pi, 4, endpoint=False):
        x = [0.88 * np.cos(angle), 0.88 * np.cos(angle)]
        y = [0.88 * np.sin(angle), 0.88 * np.sin(angle)]
        fig.add_trace(
            go.Scatter3d(
                x=x,
                y=y,
                z=[0.35, 2.35],
                mode="lines",
                line=dict(color="#e2e8f0", width=5),
                name="四块挡板",
                hovertemplate="反应釜挡板 baffle<extra></extra>",
                showlegend=False,
            )
        )
    add_pipe(fig, [(-1.55, 0.0, 0.35), (-1.05, 0.0, 0.35)], name="冷却夹套入口", color=MATERIAL_COLORS["coolant"], width=5)
    add_pipe(fig, [(1.05, 0.0, 2.45), (1.55, 0.0, 2.45)], name="冷却夹套出口", color=MATERIAL_COLORS["coolant"], width=5)
    add_pipe(fig, [(0.0, 0.0, 2.75), (0.0, 0.0, 3.25)], name="顶部气相空间/压力表", color="#ef4444", width=4)
    add_pipe(fig, [(-0.55, -1.25, 2.45), (-0.30, -0.76, 2.10)], name="气体进料管", color=MATERIAL_COLORS["ethylene"], width=4)
    add_pipe(fig, [(0.90, -1.20, 1.55), (0.58, -0.62, 1.25)], name="ENB液体进料管", color=MATERIAL_COLORS["ENB"], width=4)
    add_pipe(fig, [(-0.88, 1.18, 1.85), (-0.50, 0.62, 1.55)], name="催化剂注入口", color=MATERIAL_COLORS["catalyst"], width=4)
    add_pipe(fig, [(1.12, 0.70, 1.10), (0.72, 0.35, 1.00)], name="终止剂注入口", color="#f97316", width=4)
    add_pipe(fig, [(0.0, 0.0, 0.15), (0.0, 0.0, -0.35), (0.75, 0.0, -0.35)], name="底部出料口", color=MATERIAL_COLORS["polymer_solution"], width=6)
    add_label(fig, "T/P", (0.28, -1.0, 2.5), "#ef4444")
    add_label(fig, "液位", (-0.85, 0.2, 1.55), "#38bdf8")
    if highlighted:
        add_cylinder(fig, center=(0.0, 0.0, 1.4), radius=1.18, height=2.7, name="选中设备高亮", color="#facc15", opacity=0.10)
    _finish_3d(fig, "聚合釜3D示意")
    return fig


def flash_vessel_3d_figure(result=None, flash: str = "Flash-1") -> go.Figure:
    """Create a flash/devolatilizer 3D sketch."""
    fig = go.Figure()
    color = "#0ea5e9" if flash == "Flash-1" else "#14b8a6"
    add_cylinder(fig, center=(0.0, 0.0, 1.3), radius=0.65, height=2.1, name=flash, color=color, opacity=0.55)
    add_pipe(fig, [(-1.35, 0.0, 1.45), (-0.65, 0.0, 1.45)], name="胶液入口", color=MATERIAL_COLORS["polymer_solution"])
    add_pipe(fig, [(0.0, 0.0, 2.35), (0.0, 0.0, 3.0), (1.1, 0.0, 3.0)], name="气相回收", color=MATERIAL_COLORS["vapor_recycle"])
    add_pipe(fig, [(0.0, 0.0, 0.25), (0.0, 0.0, -0.25), (1.1, 0.0, -0.25)], name="底部胶液", color=MATERIAL_COLORS["polymer_solution"])
    _finish_3d(fig, f"{flash} 3D示意")
    return fig


def product_tank_3d_figure(result=None) -> go.Figure:
    """Create a polymer product tank sketch."""
    kpis = getattr(result, "kpis", {}) if result is not None else {}
    fig = go.Figure()
    add_cylinder(
        fig,
        center=(0.0, 0.0, 1.05),
        radius=0.85,
        height=1.9,
        name="产品罐",
        color=MATERIAL_COLORS["product"],
        opacity=0.62,
        hover=f"产品罐<br>Mooney: {kpis.get('Mooney', 0):.1f}<br>Mw: {kpis.get('Mw', 0):.0f}<extra></extra>",
    )
    add_cylinder(fig, center=(0.0, 0.0, 0.62), radius=0.75, height=1.0, name="EPDM产品", color="#312e81", opacity=0.38)
    add_label(fig, f"ML {kpis.get('Mooney', 0):.0f}", (0.0, -0.95, 1.8), "#111827")
    _finish_3d(fig, "产品罐3D示意")
    return fig


def heat_exchanger_3d_figure(result=None) -> go.Figure:
    """Create a preheater/cooling heat-exchanger sketch."""
    fig = go.Figure()
    add_cylinder(fig, center=(0.0, 0.0, 0.8), radius=0.35, height=1.8, name="管壳式换热器", color="#64748b", opacity=0.64)
    for offset in [-0.18, 0.0, 0.18]:
        add_pipe(fig, [(-1.1, offset, 0.8), (1.1, offset, 0.8)], name="换热管束", color="#f97316", width=4)
    add_pipe(fig, [(-1.45, 0.0, 0.8), (-1.1, 0.0, 0.8)], name="进料", color=MATERIAL_COLORS["solvent"])
    add_pipe(fig, [(1.1, 0.0, 0.8), (1.45, 0.0, 0.8)], name="出料", color=MATERIAL_COLORS["polymer_solution"])
    _finish_3d(fig, "换热器3D示意")
    return fig


def feed_area_3d_figure() -> go.Figure:
    """Create a feed-preparation 3D sketch."""
    fig = go.Figure()
    feeds = [
        ("乙烯钢瓶", -2.2, 0.6, MATERIAL_COLORS["ethylene"]),
        ("丙烯钢瓶", -1.2, 0.6, MATERIAL_COLORS["propylene"]),
        ("氢气钢瓶", -0.2, 0.6, MATERIAL_COLORS["hydrogen"]),
        ("ENB储罐", -1.7, -0.8, MATERIAL_COLORS["ENB"]),
        ("溶剂储罐", -0.6, -0.8, MATERIAL_COLORS["solvent"]),
    ]
    for name, x, y, color in feeds:
        add_cylinder(fig, center=(x, y, 0.85), radius=0.28, height=1.45, name=name, color=color, opacity=0.72)
    add_box(fig, center=(0.75, -0.1, 0.75), size=(0.5, 0.35, 0.35), name="催化剂/MAO/BHT计量", color=MATERIAL_COLORS["catalyst"])
    add_box(fig, center=(1.55, -0.1, 0.75), size=(0.45, 0.45, 0.45), name="混合器", color="#64748b")
    for _, x, y, color in feeds:
        add_pipe(fig, [(x, y, 0.85), (1.3, -0.1, 0.85)], name="进料线", color=color, width=4)
    add_pipe(fig, [(0.95, -0.1, 0.75), (1.35, -0.1, 0.75)], name="催化剂线", color=MATERIAL_COLORS["catalyst"], width=4)
    _finish_3d(fig, "原料罐区3D示意")
    return fig


def equipment_summary(result=None) -> pd.DataFrame:
    """Return an equipment summary table for UI and reports."""
    k = getattr(result, "kpis", {}) if result is not None else {}
    rows = [
        ["Feed", "原料区", "乙烯/丙烯/ENB/氢气/溶剂/催化剂进料", "normal"],
        ["Mixer", "反应区", "原料混合，总流量进入预热器", "normal"],
        ["Preheater", "反应区", f"预热负荷 {k.get('preheat_kW', 0):.2f} kW", "normal"],
        ["Reactor", "反应区", f"反应热 {k.get('heat_duty_kW', 0):.2f} kW，固含 {k.get('solids_wt', 0):.2f} wt%", k.get("fouling_risk", "normal")],
        ["Quench", "反应区", "终止/脱活催化剂", "normal"],
        ["Flash-1", "分离区", f"气相回收 {k.get('flash1_recycle_kg_h', 0):.2f} kg/h", "normal"],
        ["Flash-2", "分离区", f"脱挥负荷 {k.get('devol_duty_kW', 0):.2f} kW，ENB残留 {k.get('ENB_residue_ppm', 0):.0f} ppm", "normal"],
        ["Product", "产品区", f"最佳对标 {k.get('best_grade', '-')}", "normal"],
    ]
    return pd.DataFrame(rows, columns=["equipment", "section", "key_info", "status"])


def _finish_3d(fig: go.Figure, title: str) -> None:
    """Apply common 3D layout settings."""
    fig.update_layout(
        title=title,
        height=480,
        margin=dict(l=0, r=0, t=42, b=0),
        scene=dict(
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            zaxis=dict(visible=False),
            aspectmode="data",
            camera=dict(eye=dict(x=1.7, y=-1.7, z=1.2)),
        ),
        legend=dict(orientation="h", y=0.02),
    )
