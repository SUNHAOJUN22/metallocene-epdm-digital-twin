"""Main report entry point directing to Excel, PDF and Word exporters."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .reporting.excel import export_excel
from .reporting.pdf import export_pdf_report
from .reporting.word import export_word_report

__all__ = ["export_excel", "export_pdf_report", "export_word_report"]
