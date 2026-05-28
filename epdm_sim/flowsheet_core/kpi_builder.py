"""Template KPI builder wrappers."""

from __future__ import annotations

from ..kpi_adapter import build_template_kpis


def build_kpis_for_template(template_id: str, result):
    """Build template-aware KPIs from a flowsheet result."""
    return build_template_kpis(template_id, result)

