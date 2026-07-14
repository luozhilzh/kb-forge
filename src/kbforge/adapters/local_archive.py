"""Local archive adapter — ingests posts already downloaded to disk.

This is the "no external API" path. Point it at a directory of
``<year>/<month>/<date>-t<topic_id>.md`` posts (the same offline layout the
zsxq adapter mirrors) and it yields normalized :class:`Topic` objects. Body is
cleaned of platform-specific inline tags (e.g. zsxq ``<e .../>``) so the
downstream wiki is plain Markdown.

Fully offline and CI-safe — no network, no credentials.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

from ..core.clean import clean_post_body
from .base import Attachment, FetchResult, PlatformAdapter, Topic

# Strip zsxq-style inline element tags: <e .../>, <e ...>...</e>, </e>
_INLINE_ELEM_RE = re.compile(r"</?e\b[^>]*>")
# Extract the numeric topic id from a filename like 2026-07-02-t82255211218852252
_TOPIC_ID_RE = re.compile(r"t(\d+)")
_RESERVED = {"index.md", "log.md", "SCHEMA.md"}


def _clean_body(body: str) -> str:
    text = _INLINE_ELEM_RE.sub("", body)
    # collapse 3+ blank lines into 2 for tidy Markdown
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    # remove redundant truncated "## 摘要" previews (real-world export noise)
    text, _ = clean_post_body(text)
    return text


class LocalArchiveAdapter(PlatformAdapter):
    """Read posts from a local archive directory (offline)."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    # ------------------------------------------------------------------ #
    def _iter_files(self, year: str | None = None, month: str | None = None):
        if year is not None:
            base = self.root / str(year)
            if month is not None:
                base = base / f"{int(month):02d}"
        else:
            base = self.root
        if not base.exists():
            return
        for md in sorted(base.rglob("*.md")):
            if md.name in _RESERVED:
                continue
            yield md

    def scan(
        self,
        year: str | None = None,
        month: str | None = None,
        limit: int | None = None,
    ) -> list[Topic]:
        """Return normalized posts, optionally filtered by year/month and capped.

        The ``<year>/<month>`` layout from the source path is preserved on each
        ``Topic.extra["source_path"]`` so the orchestrator can replicate it.
        """
        from ..core.frontmatter import parse

        topics: list[Topic] = []
        for md in self._iter_files(year, month):
            text = md.read_text(encoding="utf-8")
            meta, body = parse(text)
            stem = md.stem
            m = _TOPIC_ID_RE.search(stem)
            topic_id = m.group(1) if m else stem
            title = (meta.get("title") or stem).strip()
            tags = meta.get("tags") or []
            if isinstance(tags, str):
                tags = [tags]
            topics.append(
                Topic(
                    topic_id=str(topic_id),
                    title=title,
                    body=_clean_body(body),
                    published_at=str(meta.get("date") or meta.get("published_at") or ""),
                    group_id=str(meta.get("group") or "local-archive"),
                    author=str(meta.get("author") or ""),
                    attachments=[],
                    tags=list(tags),
                    extra={"source_path": str(md)},
                )
            )
            if limit is not None and len(topics) >= limit:
                break
        return topics

    # PlatformAdapter contract ------------------------------------------ #
    def fetch_topics(self, cursor: str | None = None, limit: int = 50) -> FetchResult:
        topics = self.scan(limit=limit)
        return FetchResult(topics, next_cursor=None)

    def download_attachment(self, att: Attachment, dest: Path) -> Path:
        raise NotImplementedError(
            "LocalArchiveAdapter reads posts already on disk; attachments are "
            "referenced by path, not downloaded."
        )

    def paginate(self, start_cursor: str | None = None, limit: int = 50) -> Iterable[FetchResult]:
        yield self.fetch_topics(cursor=start_cursor, limit=limit)
