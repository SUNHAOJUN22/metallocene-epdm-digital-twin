"""Plotly visualization helpers."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def flowsheet_block_diagram() -> go.Figure:
    """Return a simple block flowsheet diagram."""
    labels = ["Feed", "Mixer", "Preheater", "Reactor(s)", "Quench", "Flash-1", "Flash-2", "Product"]
    x = list(range(len(labels)))
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x,
            y=[0] * len(labels),
            mode="markers+text+lines",
            text=labels,
            textposition="bottom center",
            marker=dict(size=34, color="#2563eb", symbol="square"),
            line=dict(color="#64748b", width=3),
            hoverinfo="text",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[5.4, 4.3, 3.2],
            y=[0.3, 0.65, 0.35],
            mode="lines+text",
            text=["Recycle", "", ""],
            textposition="top center",
            line=dict(color="#0f766e", width=2, dash="dot"),
            hoverinfo="skip",
        )
    )
    fig.update_layout(
        height=240,
        margin=dict(l=20, r=20, t=20, b=40),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False, range=[-0.6, 1.0]),
        showlegend=False,
    )
    return fig


def sankey_material(result) -> go.Figure:
    """Return a Sankey diagram for major material flows."""
    labels = ["Feed", "Reactor", "Flash-1 vapor", "Flash-1 liquid", "Flash-2 vapor", "Product", "Recycle/Purge"]
    source = [0, 1, 1, 3, 3, 2, 4]
    target = [1, 2, 3, 4, 5, 6, 6]
    value = [
        result.streams["Feed"].total_mass_flow(),
        result.streams["Flash-1 vapor"].total_mass_flow(),
        result.streams["Flash-1 liquid"].total_mass_flow(),
        result.streams["Flash-2 vapor"].total_mass_flow(),
        result.streams["Polymer product"].total_mass_flow(),
        result.streams["Flash-1 vapor"].total_mass_flow(),
        result.streams["Flash-2 vapor"].total_mass_flow(),
    ]
    fig = go.Figure(
        data=[
            go.Sankey(
                node=dict(label=labels, pad=15, thickness=16, color="#94a3b8"),
                link=dict(source=source, target=target, value=value, color="rgba(37,99,235,0.25)"),
            )
        ]
    )
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=20, b=10))
    return fig


def conversion_bar(result) -> go.Figure:
    """Return monomer conversion bar chart."""
    df = pd.DataFrame(
        {
            "单体": ["乙烯", "丙烯", "ENB"],
            "转化率/%": [
                result.kpis["C2_conversion_pct"],
                result.kpis["C3_conversion_pct"],
                result.kpis["ENB_conversion_pct"],
            ],
        }
    )
    fig = px.bar(df, x="单体", y="转化率/%", color="单体", text_auto=".1f")
    fig.update_layout(height=320, showlegend=False, margin=dict(l=10, r=10, t=30, b=10))
    return fig


def composition_bar(result) -> go.Figure:
    """Return product composition stacked bar."""
    df = pd.DataFrame(
        {
            "segment": ["乙烯", "丙烯", "ENB"],
            "wt%": [result.kpis["C2_wt"], result.kpis["C3_wt"], result.kpis["ENB_wt"]],
        }
    )
    fig = px.bar(df, x=["产品"] * len(df), y="wt%", color="segment", text="wt%")
    fig.update_traces(texttemplate="%{text:.1f}%")
    fig.update_layout(height=280, xaxis_title="", yaxis_title="wt%", margin=dict(l=10, r=10, t=30, b=10))
    return fig


def flash_split_chart(flash_result) -> go.Figure:
    """Return vapor/liquid split chart."""
    df = flash_result.split_table.copy()
    if df.empty:
        return go.Figure()
    fig = go.Figure()
    fig.add_bar(name="气相 kg/h", x=df["component"], y=df["vapor_kg_h"])
    fig.add_bar(name="液相 kg/h", x=df["component"], y=df["liquid_kg_h"])
    fig.update_layout(barmode="stack", height=330, margin=dict(l=10, r=10, t=30, b=10))
    return fig


def sensitivity_line(df: pd.DataFrame, y: str) -> go.Figure:
    """Return line plot for one-dimensional sensitivity results."""
    fig = px.line(df, x="value", y=y, markers=True)
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=30, b=10), xaxis_title="扫描变量")
    return fig


def sensitivity_heatmap(df: pd.DataFrame, x: str, y: str, z: str) -> go.Figure:
    """Return heatmap for two-dimensional sensitivity results."""
    pivot = df.pivot_table(index=y, columns=x, values=z, aggfunc="mean")
    fig = px.imshow(pivot, aspect="auto", color_continuous_scale="Viridis")
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=30, b=10))
    return fig


def optimization_convergence(history: list[dict[str, float]]) -> go.Figure:
    """Return optimization convergence plot."""
    df = pd.DataFrame(history)
    if df.empty:
        return go.Figure()
    fig = px.line(df, x="iteration", y="objective", markers=True)
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=30, b=10), yaxis_title="目标函数")
    return fig


def property_curve(df: pd.DataFrame, x: str, y: str, title: str, y_title: str | None = None) -> go.Figure:
    """Return a generic property curve plot."""
    fig = px.line(df, x=x, y=y, markers=True, title=title)
    fig.update_layout(
        height=320,
        margin=dict(l=10, r=10, t=45, b=10),
        yaxis_title=y_title or y,
    )
    return fig
