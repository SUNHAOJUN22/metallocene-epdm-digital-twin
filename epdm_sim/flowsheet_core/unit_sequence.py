"""Flowsheet unit-sequence metadata."""

from __future__ import annotations


def default_unit_sequence() -> list[str]:
    """Return the default EPDM solution-polymerization unit sequence."""
    return ["feed", "reactor", "flash1", "flash2", "product", "recycle"]

