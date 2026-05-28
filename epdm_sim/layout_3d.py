"""3D process-layout builder for the EPDM digital twin."""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

from .equipment_3d import (
    MATERIAL_COLORS,
    add_box,
    add_cylinder,
    add_label,
    add_pipe,
    risk_color_from_kpis,
)


EQUIPMENT_POSITIONS = {
    "Ethylene": (-5.5, 1.8, 0.8),
    "Propylene": (-4.6, 1.8, 0.8),
    "Hydrogen": (-3.7, 1.8, 0.8),
    "ENB": (-5.0, 0.4, 0.8),
    "Solvent": (-3.9, 0.4, 0.8),
    "CatalystSkid": (-2.7, 0.4, 0.7),
    "Mixer": (-1.5, 1.0, 0.8),
    "Preheater": (-0.3, 1.0, 0.8),
    "Reactor1": (1.1, 1.0, 1.2),
    "Reactor2": (2.5, 1.0, 1.2),
    "Quench": (3.8, 1.0, 0.9),
    "Flash1": (5.1, 1.0, 1.2),
    "Flash2": (6.5, 1.0, 1.2),
    "Condenser": (5.8, 2.6, 1.8),
    "Compressor": (4.5, 2.8, 0.8),
    "RecycleTank": (2.7, 2.7, 0.8),
    "Pump": (4.2, -0.45, 0.35),
    "Product": (7.8, 0.6, 1.0),
}


def process_3d_layout(result=None, mode: str = "物料流模式", highlight: str | None = None) -> go.Figure:
    """Build an interactive 3D process overview layout."""
    kpis: dict[str, Any] = getattr(result, "kpis", {}) if result is not None else {}
    fig = go.Figure()

    _draw_section_platforms(fig)
    _draw_feed_area(fig)
    _draw_reaction_area(fig, kpis, mode, highlight)
    _draw_separation_area(fig, kpis, highlight)
    _draw_recycle_system(fig)
    _draw_transfer_lines(fig)

    if highlight and highlight in EQUIPMENT_POSITIONS:
        x, y, z = EQUIPMENT_POSITIONS[highlight]
        add_cylinder(fig, center=(x, y, z), radius=0.55, height=1.45, name=f"高亮 {highlight}", color="#facc15", opacity=0.18)

    fig.update_layout(
        title="茂金属EPM/EPDM溶液聚合数字孪生 3D装置总览",
        height=560,
        margin=dict(l=0, r=0, t=42, b=0),
        scene=dict(
            xaxis=dict(title="", visible=False),
            yaxis=dict(title="", visible=False),
            zaxis=dict(title="", visible=False),
            aspectmode="data",
            camera=dict(eye=dict(x=1.55, y=-1.75, z=1.05)),
        ),
        legend=dict(orientation="h", y=0.02),
    )
    return fig


def _draw_section_platforms(fig: go.Figure) -> None:
    """Draw translucent industrial-area platforms under process sections."""
    platform_specs = [
        ("原料罐区", (-4.55, 1.08, -0.06), (2.65, 1.95, 0.06), "#0ea5e9"),
        ("催化剂计量区", (-2.65, 0.38, -0.05), (0.85, 0.85, 0.06), "#ef4444"),
        ("聚合反应区", (1.6, 0.92, -0.06), (4.35, 1.55, 0.06), "#8b5cf6"),
        ("分离脱挥区", (5.9, 1.02, -0.06), (2.45, 1.55, 0.06), "#14b8a6"),
        ("回收循环区", (4.4, 2.72, -0.06), (4.35, 0.95, 0.06), "#06b6d4"),
        ("产品收集区", (7.75, 0.55, -0.06), (1.25, 1.20, 0.06), "#334155"),
    ]
    for label, center, size, color in platform_specs:
        add_box(fig, center=center, size=size, name=label, color=color, opacity=0.20)
        add_label(fig, label, (center[0], center[1], 0.10), "#e5e7eb")


def _draw_feed_area(fig: go.Figure) -> None:
    """Draw feed tanks and cylinders."""
    feed_specs = [
        ("乙烯", "Ethylene", MATERIAL_COLORS["ethylene"]),
        ("丙烯", "Propylene", MATERIAL_COLORS["propylene"]),
        ("氢气", "Hydrogen", MATERIAL_COLORS["hydrogen"]),
        ("ENB", "ENB", MATERIAL_COLORS["ENB"]),
        ("溶剂", "Solvent", MATERIAL_COLORS["solvent"]),
    ]
    for label, key, color in feed_specs:
        x, y, z = EQUIPMENT_POSITIONS[key]
        add_cylinder(fig, center=(x, y, z), radius=0.25, height=1.3, name=f"{label}储罐/钢瓶", color=color, opacity=0.75)
        add_label(fig, label, (x, y, z + 0.85))
    x, y, z = EQUIPMENT_POSITIONS["CatalystSkid"]
    add_box(fig, center=(x, y, z), size=(0.45, 0.35, 0.35), name="催化剂/MAO/BHT计量", color=MATERIAL_COLORS["catalyst"])


def _draw_reaction_area(fig: go.Figure, kpis: dict[str, Any], mode: str, highlight: str | None) -> None:
    """Draw mixer, preheater, reactor train and quench vessel."""
    add_box(fig, center=EQUIPMENT_POSITIONS["Mixer"], size=(0.35, 0.35, 0.35), name="混合器", color="#475569")
    add_cylinder(fig, center=EQUIPMENT_POSITIONS["Preheater"], radius=0.25, height=0.9, name="预热器", color="#f97316", opacity=0.68)
    reactor_color = risk_color_from_kpis(kpis, mode)
    for idx, key in enumerate(["Reactor1", "Reactor2"], start=1):
        add_cylinder(
            fig,
            center=EQUIPMENT_POSITIONS[key],
            radius=0.42,
            height=1.55,
            name=f"CSTR-{idx}",
            color=reactor_color,
            opacity=0.58,
            hover=(
                f"CSTR-{idx}<br>反应热 {kpis.get('heat_duty_kW', 0):.2f} kW<br>"
                f"黏度 {kpis.get('dynamic_viscosity_Pa_s', 0):.4g} Pa.s<br>"
                f"挂胶风险 {kpis.get('fouling_risk', 'n/a')}<extra></extra>"
            ),
        )
        add_cylinder(fig, center=(EQUIPMENT_POSITIONS[key][0], EQUIPMENT_POSITIONS[key][1], 0.85), radius=0.36, height=0.8, name="釜内胶液", color=MATERIAL_COLORS["polymer_solution"], opacity=0.28)
        if highlight == key:
            add_cylinder(fig, center=EQUIPMENT_POSITIONS[key], radius=0.50, height=1.7, name=f"高亮 {key}", color="#facc15", opacity=0.16)
    add_cylinder(fig, center=EQUIPMENT_POSITIONS["Quench"], radius=0.32, height=1.05, name="终止/脱活器", color="#94a3b8", opacity=0.68)


def _draw_separation_area(fig: go.Figure, kpis: dict[str, Any], highlight: str | None) -> None:
    """Draw flash vessels, condenser and product tank."""
    add_cylinder(fig, center=EQUIPMENT_POSITIONS["Flash1"], radius=0.36, height=1.55, name="一级闪蒸罐", color="#0ea5e9", opacity=0.60)
    add_cylinder(fig, center=EQUIPMENT_POSITIONS["Flash2"], radius=0.38, height=1.75, name="二级闪蒸/脱挥器", color="#14b8a6", opacity=0.60)
    add_cylinder(fig, center=EQUIPMENT_POSITIONS["Condenser"], radius=0.23, height=0.95, name="冷凝器", color="#38bdf8", opacity=0.64)
    add_box(fig, center=EQUIPMENT_POSITIONS["Compressor"], size=(0.36, 0.32, 0.28), name="回收压缩机", color="#06b6d4")
    add_cylinder(fig, center=EQUIPMENT_POSITIONS["RecycleTank"], radius=0.32, height=1.1, name="溶剂/ENB回收罐", color="#d1b45f", opacity=0.62)
    add_box(fig, center=EQUIPMENT_POSITIONS["Pump"], size=(0.35, 0.24, 0.24), name="胶液输送泵", color="#312e81")
    add_cylinder(
        fig,
        center=EQUIPMENT_POSITIONS["Product"],
        radius=0.46,
        height=1.55,
        name="产品罐",
        color=MATERIAL_COLORS["product"],
        opacity=0.62,
        hover=f"产品罐<br>产品 {kpis.get('polymer_kg_h', 0):.2f} kg/h<br>对标 {kpis.get('best_grade', '-')}<extra></extra>",
    )


def _draw_transfer_lines(fig: go.Figure) -> None:
    """Draw material, recycle and product transfer lines."""
    # Feed lines to mixer
    for key, color in [
        ("Ethylene", MATERIAL_COLORS["ethylene"]),
        ("Propylene", MATERIAL_COLORS["propylene"]),
        ("Hydrogen", MATERIAL_COLORS["hydrogen"]),
        ("ENB", MATERIAL_COLORS["ENB"]),
        ("Solvent", MATERIAL_COLORS["solvent"]),
        ("CatalystSkid", MATERIAL_COLORS["catalyst"]),
    ]:
        p0 = EQUIPMENT_POSITIONS[key]
        p1 = EQUIPMENT_POSITIONS["Mixer"]
        add_pipe(fig, [(p0[0], p0[1], p0[2]), (p1[0], p1[1], p1[2])], name=f"{key}进料", color=color, width=3)
    sequence = ["Mixer", "Preheater", "Reactor1", "Reactor2", "Quench", "Flash1", "Flash2", "Product"]
    for a, b in zip(sequence[:-1], sequence[1:]):
        color = MATERIAL_COLORS["solvent"] if a in ["Mixer", "Preheater"] else MATERIAL_COLORS["polymer_solution"]
        add_pipe(fig, [EQUIPMENT_POSITIONS[a], EQUIPMENT_POSITIONS[b]], name=f"{a}->{b}", color=color, width=6)
    add_pipe(fig, [EQUIPMENT_POSITIONS["Flash1"], EQUIPMENT_POSITIONS["Condenser"], EQUIPMENT_POSITIONS["Compressor"], EQUIPMENT_POSITIONS["Mixer"]], name="C2/C3/H2气相回收", color=MATERIAL_COLORS["vapor_recycle"], width=5, dash="dash")
    add_pipe(fig, [EQUIPMENT_POSITIONS["Flash2"], EQUIPMENT_POSITIONS["Condenser"], EQUIPMENT_POSITIONS["RecycleTank"], EQUIPMENT_POSITIONS["Mixer"]], name="溶剂/ENB回收", color=MATERIAL_COLORS["solvent"], width=5, dash="dash")
    add_pipe(fig, [EQUIPMENT_POSITIONS["Flash2"], EQUIPMENT_POSITIONS["Pump"], EQUIPMENT_POSITIONS["Product"]], name="产品胶液输送", color=MATERIAL_COLORS["product"], width=6)


def _draw_recycle_system(fig: go.Figure) -> None:
    """Add section labels."""
    add_label(fig, "原料区", (-4.7, 2.65, 1.7), "#334155")
    add_label(fig, "反应区", (1.4, 0.0, 2.2), "#334155")
    add_label(fig, "分离与回收区", (5.6, 3.2, 2.4), "#334155")
    add_label(fig, "产品区", (7.8, -0.2, 2.0), "#334155")
