"""Pipeline orchestrator (the ``run_all`` entry used by CLI / B / expert)."""

from __future__ import annotations

from pathlib import Path

from ..config import KbForgeConfig
from .wiki.build_index import build_index
from .wiki.ingest import ingest_post, serialize_page
from .wiki.schema import parse_schema, validate_pages_against_schema

_RESERVED = {"index.md", "log.md"}


def run(
    cfg: KbForgeConfig,
    stage: str | None = None,
    topic: str | None = None,
    dry_run: bool = False,
) -> dict:
    """Run the thin slice: ingest archive -> compile wiki -> build index.

    ``stage``:
      * None / "wiki" — ingest + index (full MVP slice)
      * "ingest"      — only write wiki pages
      * "index"       — only rebuild index from existing pages
    """
    archive_dir = cfg.path("archive")
    wiki_dir = cfg.path("wiki")
    if not dry_run:
        wiki_dir.mkdir(parents=True, exist_ok=True)

    # --- ingest ---
    pages = []
    if stage in (None, "wiki", "ingest"):
        for md in sorted(archive_dir.glob("**/*.md")):
            if md.name in _RESERVED:
                continue
            if topic and topic not in md.stem:
                continue
            pages.append(ingest_post(md))
        writes = []
        if not dry_run:
            for p in pages:
                out = wiki_dir / f"{p.slug}.md"
                out.write_text(serialize_page(p), encoding="utf-8")
                writes.append(str(out))
    else:
        writes = []

    # --- schema (advisory) ---
    schema_path = cfg.root / cfg.wiki.schema_path
    schema_topics = parse_schema(schema_path)
    warnings = validate_pages_against_schema(pages, schema_topics)

    # --- build index ---
    if stage in (None, "wiki", "index") and not dry_run:
        build_index(wiki_dir)

    return {
        "ingested": len(pages),
        "wiki_writes": writes,
        "schema_warnings": warnings,
        "dry_run": dry_run,
    }
