"""Shared rendering helpers for Word and PDF report exporters."""

from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd


def _figure_to_png(fig: Any) -> bytes:
    """Render a Plotly figure to PNG bytes when kaleido is available."""
    if not hasattr(fig, "to_image"):
        raise TypeError("figure object does not support to_image")
    return fig.to_image(format="png", width=1100, height=620, scale=2)


def _append_docx_figures(document: Any, figures: dict[str, Any], Inches: Any) -> list[str]:
    """Append static Plotly figures to a Word document, returning fallback notes."""
    notes: list[str] = []
    for title, fig in figures.items():
        try:
            image = BytesIO(_figure_to_png(fig))
            document.add_heading(str(title), level=2)
            document.add_picture(image, width=Inches(6.2))
        except Exception as exc:
            notes.append(f"{title}: kaleido/静态图导出不可用，已保留表格摘要。原因：{exc}")
    return notes


def _append_pdf_figures(story: list[Any], figures: dict[str, Any], Image: Any, base: Any) -> list[str]:
    """Append static Plotly figures to a PDF story, returning fallback notes."""
    from reportlab.platypus import Paragraph

    notes: list[str] = []
    for title, fig in figures.items():
        try:
            image = BytesIO(_figure_to_png(fig))
            story.append(Paragraph(str(title), base))
            story.append(Image(image, width=470, height=265))
        except Exception as exc:
            notes.append(f"{title}: kaleido/静态图导出不可用，已保留表格摘要。原因：{exc}")
    return notes


def _table(rows: list[list[str]]):
    """Create a styled reportlab table."""
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle

    table = Table(rows, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), "STSong-Light"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    return table


def _docx_table(document: Any, rows: list[list[str]]) -> None:
    """Append a simple Word table from rows."""
    table = document.add_table(rows=len(rows), cols=len(rows[0]))
    table.style = "Table Grid"
    for i, row in enumerate(rows):
        for j, value in enumerate(row):
            table.cell(i, j).text = str(value)


def _docx_dataframe(document: Any, df: pd.DataFrame, max_rows: int = 20) -> None:
    """Append a compact DataFrame table to a Word document."""
    shown = df.head(max_rows)
    table = document.add_table(rows=len(shown) + 1, cols=len(shown.columns))
    table.style = "Table Grid"
    for j, col in enumerate(shown.columns):
        table.cell(0, j).text = str(col)
    for i, (_, row) in enumerate(shown.iterrows(), start=1):
        for j, col in enumerate(shown.columns):
            table.cell(i, j).text = str(row[col])
