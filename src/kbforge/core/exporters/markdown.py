"""Markdown exporter — a minimal, OKF-compatible bundle renderer.

The bundle file itself carries a ``type: bundle`` frontmatter so the OKF golden
test can validate exporter output too (not just wiki pages).
"""

from __future__ import annotations

import yaml
from pathlib import Path

from .base import BaseExporter


class MarkdownExporter(BaseExporter):
    name = "markdown"
    suffix = ".md"

    def export(self, pages: list, out_path: Path) -> Path:
        out_path = out_path.with_suffix(".md")
        head = yaml.safe_dump(
            {"type": "bundle", "title": "kb-forge export", "pages": len(pages)},
            allow_unicode=True,
            sort_keys=False,
        ).strip()
        parts = [f"---\n{head}\n---", ""]
        for p in pages:
            meta = getattr(p, "meta", {})
            title = meta.get("title", getattr(p, "slug", "page"))
            parts.append(f"## {title}")
            parts.append("")
            parts.append(getattr(p, "body", "").strip())
            parts.append("")
        out_path.write_text("\n".join(parts), encoding="utf-8")
        return out_path
