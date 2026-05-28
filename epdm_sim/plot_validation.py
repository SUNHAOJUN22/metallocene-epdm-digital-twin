"""Plotly figure validation for scientific visualization release gates."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

import pandas as pd
import plotly.graph_objects as go


UNIT_TOKENS = (
    "%",
    "wt%",
    "kg/h",
    "mol",
    "kW",
    "kJ",
    "K",
    "°C",
    "MPa",
    "kPa",
    "Pa",
    "Pa.s",
    "Pa·s",
    "m/s",
    "1/s",
)


@dataclass(frozen=True)
class PlotValidationResult:
    """One figure validation result."""

    figure_name: str
    check: str
    passed: bool
    severity: str
    message: str


def _axis_title(fig: go.Figure, axis: str) -> str:
    """Return a layout axis title as text."""
    obj = getattr(fig.layout, axis, None)
    title = getattr(obj, "title", None)
    text = getattr(title, "text", "") if title is not None else ""
    return str(text or "")


def _trace_name(trace: Any) -> str:
    return str(getattr(trace, "name", "") or "")


def _trace_hover(trace: Any) -> str:
    return str(getattr(trace, "hovertemplate", "") or getattr(trace, "hoverinfo", "") or "")


def _has_unit_text(text: str) -> bool:
    return any(token in text for token in UNIT_TOKENS)


def validate_nonempty_figure(fig: go.Figure, figure_name: str = "figure") -> list[PlotValidationResult]:
    """Validate a figure has renderable traces."""
    return [
        PlotValidationResult(
            figure_name,
            "nonempty_data",
            bool(getattr(fig, "data", ())),
            "error",
            "figure.data must not be empty",
        )
    ]


def validate_axis_labels(fig: go.Figure, figure_name: str = "figure") -> list[PlotValidationResult]:
    """Validate axis labels for 2D numeric plots.

    Sankey and 3D schematic plots are excluded from strict axis-title checks
    because they do not use Cartesian scientific axes.
    """
    trace_types = {str(getattr(trace, "type", "")) for trace in fig.data}
    if not trace_types or trace_types.intersection({"sankey", "surface", "scatter3d", "cone", "mesh3d"}):
        return [PlotValidationResult(figure_name, "axis_labels", True, "info", "axis labels not required for schematic/3D/sankey figure")]
    x_title = _axis_title(fig, "xaxis")
    y_title = _axis_title(fig, "yaxis")
    passed = bool(x_title or fig.layout.xaxis.visible is False) and bool(y_title or fig.layout.yaxis.visible is False)
    return [
        PlotValidationResult(
            figure_name,
            "axis_labels",
            passed,
            "warning",
            f"xaxis='{x_title}', yaxis='{y_title}'",
        )
    ]


def validate_colorbar_labels(fig: go.Figure, figure_name: str = "figure") -> list[PlotValidationResult]:
    """Validate contour/surface-like traces expose a colorbar or hover units."""
    rows: list[PlotValidationResult] = []
    for idx, trace in enumerate(fig.data):
        trace_type = str(getattr(trace, "type", ""))
        if trace_type not in {"contour", "heatmap", "surface"}:
            continue
        colorbar = getattr(trace, "colorbar", None)
        title = getattr(getattr(colorbar, "title", None), "text", "") if colorbar is not None else ""
        hover = _trace_hover(trace)
        passed = bool(title) or _has_unit_text(hover) or _has_unit_text(_trace_name(trace))
        rows.append(
            PlotValidationResult(
                figure_name,
                f"colorbar_or_hover_units_trace_{idx}",
                passed,
                "warning",
                f"trace={trace_type}, colorbar='{title}', name='{_trace_name(trace)}'",
            )
        )
    return rows or [PlotValidationResult(figure_name, "colorbar_labels", True, "info", "no contour/heatmap/surface traces")]


def validate_plotly_figure_units(fig: go.Figure, figure_name: str = "figure") -> list[PlotValidationResult]:
    """Run nonempty, axis and colorbar validations for one figure."""
    rows = []
    rows.extend(validate_nonempty_figure(fig, figure_name))
    rows.extend(validate_axis_labels(fig, figure_name))
    rows.extend(validate_colorbar_labels(fig, figure_name))
    return rows


def plot_validation_dataframe(figures: Mapping[str, go.Figure]) -> pd.DataFrame:
    """Return validation results for a mapping of named Plotly figures."""
    rows: list[PlotValidationResult] = []
    for name, fig in figures.items():
        rows.extend(validate_plotly_figure_units(fig, name))
    return pd.DataFrame([asdict(row) for row in rows])
