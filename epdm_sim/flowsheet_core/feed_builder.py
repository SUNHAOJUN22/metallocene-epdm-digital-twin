"""Template feed-building helpers."""

from __future__ import annotations

from ..feed_adapter import build_template_feed_stream
from ..template_config import TemplateProcessConfig


def build_feed_from_template_config(config: TemplateProcessConfig):
    """Build a feed stream from a template process config."""
    return build_template_feed_stream(config)

