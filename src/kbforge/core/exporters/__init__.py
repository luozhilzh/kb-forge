"""Pluggable output layer.

``extract`` produces a structured bundle (pages); each exporter renders it to a
format. Add a format by subclassing :class:`BaseExporter` and registering it in
``EXPORTERS`` — no other code changes.
"""

from .base import BaseExporter
from .markdown import MarkdownExporter
from .pptx import PptxExporter
from .html import HtmlExporter
from .extract import CaseBundle, extract_bundles, bundles_from_pages

__all__ = [
    "BaseExporter",
    "MarkdownExporter",
    "PptxExporter",
    "HtmlExporter",
    "CaseBundle",
    "extract_bundles",
    "bundles_from_pages",
    "EXPORTERS",
]


EXPORTERS: dict[str, type[BaseExporter]] = {
    "md": MarkdownExporter,
    "pptx": PptxExporter,
    "html": HtmlExporter,
}


def get_exporter(name: str) -> BaseExporter:
    if name not in EXPORTERS:
        raise KeyError(f"Unknown exporter '{name}'. Known: {sorted(EXPORTERS)}")
    return EXPORTERS[name]()
