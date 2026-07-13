"""Pluggable output layer.

``extract`` produces a structured bundle (pages); each exporter renders it to a
format. Add a format by subclassing :class:`BaseExporter` and registering it in
``EXPORTERS`` — no other code changes.
"""

from .base import BaseExporter
from .markdown import MarkdownExporter

__all__ = ["BaseExporter", "MarkdownExporter", "EXPORTERS"]

EXPORTERS: dict[str, type[BaseExporter]] = {
    "md": MarkdownExporter,
    # "pptx": PptxExporter,   # Phase 2
    # "html": HtmlExporter,   # Phase 2
}


def get_exporter(name: str) -> BaseExporter:
    if name not in EXPORTERS:
        raise KeyError(f"Unknown exporter '{name}'. Known: {sorted(EXPORTERS)}")
    return EXPORTERS[name]()
