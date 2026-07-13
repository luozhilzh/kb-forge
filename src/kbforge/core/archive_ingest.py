"""End-to-end ingest of a local archive into a self-contained KB root.

The output layout is identical to what ``make-fixtures`` produces, so every
downstream stage (build / query / site / export / enrich / diff / mcp) works
unchanged:

  <out>/archive/<year>/<month>/<file>.md   (normalized OKF posts)
  <out>/SCHEMA.md                          (minimal page-type schema)
  <out>/wiki/...                           (compiled wiki + index + graph)

Offline: reads posts already on disk, never touches a platform API.
"""

from __future__ import annotations

from pathlib import Path

from ..adapters.local_archive import LocalArchiveAdapter
from ..config import KbForgeConfig, PathsConfig
from .frontmatter import dump
from .pipeline import run


def _write_post(out_archive: Path, rel: Path, topic) -> None:
    out = out_archive / rel
    out.parent.mkdir(parents=True, exist_ok=True)
    meta = {
        "type": "post",
        "title": topic.title,
        "topic_id": topic.topic_id,
        "author": topic.author,
        "published_at": topic.published_at,
        "tags": topic.tags,
        "sources": [topic.extra.get("source_path", "")],
    }
    out.write_text(dump(meta, topic.body), encoding="utf-8")


def ingest_archive(
    source_root: str | Path,
    out_root: str | Path,
    *,
    year: str | None = None,
    month: str | None = None,
    limit: int | None = None,
    dry_run: bool = False,
) -> dict:
    """Ingest a local archive into a self-contained KB root (offline).

    ``source_root`` is the directory holding ``<year>/<month>/*.md`` posts.
    ``out_root`` is created; it gets a normalized ``archive/`` copy plus a
    compiled ``wiki/``. Use ``year``/``month`` (e.g. ``2026``/``07``) to ingest
    only a slice, or ``limit`` to cap the post count.
    """
    source_root = Path(source_root)
    out_root = Path(out_root)

    adapter = LocalArchiveAdapter(source_root)
    topics = adapter.scan(year=year, month=month, limit=limit)

    out_archive = out_root / "archive"
    writes: list[str] = []
    if not dry_run:
        out_root.mkdir(parents=True, exist_ok=True)
        # SCHEMA.md is the allow-list of valid tags (per wiki/schema.py). Seed it
        # with the tags discovered in this ingest so validation stays quiet for
        # a real, free-form-tagged archive.
        schema_path = out_root / "SCHEMA.md"
        if not schema_path.exists():
            all_tags = sorted({t for top in topics for t in top.tags if t})
            lines = ["# 知识库主题（由 ingest-archive 自动采集）", ""]
            lines += [f"## {tag}" for tag in all_tags]
            lines.append("")
            schema_path.write_text("\n".join(lines), encoding="utf-8")
        for t in topics:
            rel = Path(t.extra["source_path"]).relative_to(source_root)
            _write_post(out_archive, rel, t)
            writes.append(str(out_archive / rel))

    # compile the wiki from the normalized copy
    cfg = KbForgeConfig(
        root=out_root,
        paths=PathsConfig(archive="archive", wiki="wiki"),
    )
    report = run(cfg, dry_run=dry_run)
    report["ingested_sources"] = len(topics)
    report["archive_writes"] = writes
    return report
