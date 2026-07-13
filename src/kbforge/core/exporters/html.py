"""HTML exporter — a standalone, self-contained page per bundle.

Renders a :class:`CaseBundle` list to a single HTML file (UTF-8, inline CSS).
No external assets, so it opens anywhere and CI can grep its content.
"""

from __future__ import annotations

import html
from pathlib import Path

from .base import BaseExporter
from .extract import CaseBundle


class HtmlExporter(BaseExporter):
    name = "html"
    suffix = ".html"

    def export(self, pages: list[CaseBundle], out_path: Path) -> Path:
        out_path = out_path.with_suffix(".html")
        parts = [
            "<!DOCTYPE html>",
            "<html lang='zh-CN'>",
            "<head><meta charset='utf-8'>",
            "<meta name='viewport' content='width=device-width, initial-scale=1'>",
            "<title>kb-forge 导出</title>",
            "<style>",
            "body{font-family:system-ui,'PingFang SC','Microsoft YaHei',sans-serif;"
            "max-width:820px;margin:2rem auto;padding:0 1rem;line-height:1.6;color:#222}",
            "h1{font-size:1.6rem;border-bottom:2px solid #4a6;padding-bottom:.3rem}",
            "section{border:1px solid #ddd;border-radius:8px;padding:1rem 1.2rem;"
            "margin:1rem 0;background:#fafafa}",
            "h2{margin-top:0;color:#2a5}",
            ".type{display:inline-block;background:#2a5;color:#fff;border-radius:4px;"
            "padding:0 .4rem;font-size:.75rem;vertical-align:middle;margin-left:.4rem}",
            ".summary{color:#555;font-style:italic}",
            ".sources,.related{font-size:.85rem;color:#666}",
            "</style></head><body>",
            f"<h1>kb-forge 导出（{len(pages)} 条）</h1>",
        ]
        for b in pages:
            parts.append(
                f"<section data-type='{html.escape(b.type)}' data-id='{html.escape(b.id)}'>"
            )
            parts.append(
                f"<h2>{html.escape(b.title)}<span class='type'>{html.escape(b.type)}</span></h2>"
            )
            if b.summary:
                parts.append(f"<p class='summary'>{html.escape(b.summary)}</p>")
            if b.content:
                parts.append(f"<div class='content'>{html.escape(b.content)}</div>")
            if b.source_anchor:
                items = "".join(f"<li>{html.escape(s)}</li>" for s in b.source_anchor)
                parts.append(f"<ul class='sources'>来源：{items}</ul>")
            if b.related:
                items = "".join(f"<li>[[{html.escape(r)}]]</li>" for r in b.related)
                parts.append(f"<ul class='related'>相关：{items}</ul>")
            parts.append("</section>")
        parts.append("</body></html>")

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("\n".join(parts), encoding="utf-8")
        return out_path
