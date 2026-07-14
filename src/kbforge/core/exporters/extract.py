"""Extract structured case bundles from compiled wiki pages.

This is the bridge between the wiki layer (Phase 0) and the exporter layer
(Phase 2). It reads already-built ``wiki/*.md`` pages, keeps only the page
types that make sense as "cases", and produces :class:`CaseBundle` objects
that every exporter (markdown / pptx / html) renders uniformly.

Design notes (aligned with §5 / §11 decisions):
  * Source = wiki pages, NOT raw archive posts (user-chosen fork A).
  * Deterministic, zero external model/vector dependency (local-first).
  * ``source_anchor`` is taken verbatim from the page ``sources`` frontmatter
    so claims stay anchored to their origin (enrich rule: claim must cite).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..frontmatter import parse
from ..wiki.build_index import extract_links
from ..wiki import WikiPage

# Page types that are worth surfacing as standalone cases/slides.
DEFAULT_TYPES = frozenset({"case", "pitfall", "concept"})

_RESERVED = {"index.md", "log.md"}

_BLOCK_RE = re.compile(r"\n\s*\n")
# A line that is a markdown heading or a bare image embed — not prose.
_NON_PROSE_RE = re.compile(r"^\s*(#{1,6}\s+\S+|!\[[^\]]*\]\([^)]*\)\s*)$")


def _first_paragraph(body: str, limit: int = 120) -> str:
    """Use the first non-empty prose paragraph as a short summary.

    Markdown heading lines (e.g. ``## 正文``) and bare image embeds are skipped
    so the derived summary is clean prose, not a section heading.
    """
    for para in _BLOCK_RE.split(body.strip()):
        lines = [ln for ln in para.splitlines() if ln.strip() and not _NON_PROSE_RE.match(ln)]
        prose = " ".join(lines).strip()
        if prose:
            return prose if len(prose) <= limit else prose[: limit - 1].rstrip() + "…"
    return ""


@dataclass
class CaseBundle:
    """A structured, exporter-agnostic representation of one wiki page."""

    id: str
    type: str
    title: str
    tags: list[str] = field(default_factory=list)
    summary: str = ""
    content: str = ""
    source_anchor: list[str] = field(default_factory=list)
    related: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)


def _page_to_bundle(slug: str, meta: dict[str, Any], body: str) -> CaseBundle:
    return CaseBundle(
        id=slug,
        type=str(meta.get("type", "unknown")),
        title=str(meta.get("title", slug)),
        tags=list(meta.get("tags", []) or []),
        summary=_first_paragraph(body),
        content=body.strip(),
        source_anchor=[str(s) for s in (meta.get("sources", []) or [])],
        related=extract_links(body),
        meta=meta,
    )


def extract_bundles(
    wiki_dir: Path,
    types: frozenset[str] = DEFAULT_TYPES,
) -> list[CaseBundle]:
    """Read ``wiki_dir/*.md`` (non-reserved), keep ``types``, return bundles."""
    wiki_dir = Path(wiki_dir)
    bundles: list[CaseBundle] = []
    for md in sorted(wiki_dir.glob("*.md")):
        if md.name in _RESERVED:
            continue
        meta, body = parse(md.read_text(encoding="utf-8"))
        ptype = str(meta.get("type", ""))
        if types and ptype not in types:
            continue
        bundles.append(_page_to_bundle(md.stem, meta, body))
    return bundles


def bundles_from_pages(pages: list[WikiPage]) -> list[CaseBundle]:
    """Build bundles directly from in-memory WikiPage objects (no disk read)."""
    out: list[CaseBundle] = []
    for p in pages:
        if p.meta.get("type") not in DEFAULT_TYPES:
            continue
        out.append(_page_to_bundle(p.slug, p.meta, p.body))
    return out
