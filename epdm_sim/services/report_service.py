"""Report export service and Plotly image fallback helpers."""

from __future__ import annotations

from typing import Any

from ..report import export_excel, export_pdf_report, export_word_report


def export_bundle(result: Any, *, report_type: str = "excel", figures: dict[str, Any] | None = None, **kwargs: Any) -> bytes:
    """Export one report type without rerunning expensive models."""
    if report_type == "word":
        return export_word_report(result, figures=figures, **kwargs)
    if report_type == "pdf":
        return export_pdf_report(result, figures=figures, **kwargs)
    return export_excel(result, **kwargs)


def figure_export_status(figures: dict[str, Any] | None) -> list[str]:
    """Return static image export readiness notes for Plotly figures."""
    notes: list[str] = []
    for name, fig in (figures or {}).items():
        if hasattr(fig, "to_image"):
            notes.append(f"{name}: 可尝试 kaleido 静态导出")
        else:
            notes.append(f"{name}: 非Plotly图对象，将使用表格摘要")
    if not notes:
        notes.append("未选择静态图，报告将导出表格摘要。")
    return notes
