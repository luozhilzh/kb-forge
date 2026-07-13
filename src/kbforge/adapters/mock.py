"""In-memory mock adapter for tests (no network, no credentials)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from .base import Attachment, FetchResult, PlatformAdapter, Topic


class MockAdapter(PlatformAdapter):
    def __init__(self, topics: list[Topic]) -> None:
        self._topics = list(topics)

    def fetch_topics(self, cursor: str | None = None, limit: int = 50) -> FetchResult:
        return FetchResult(self._topics, next_cursor=None)

    def download_attachment(self, att: Attachment, dest: Path) -> Path:
        # In tests we never actually fetch; return the intended destination.
        dest_path = dest / att.name if dest.is_dir() else dest
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_text(f"mock attachment: {att.name}\n", encoding="utf-8")
        return dest_path

    def paginate(self, start_cursor: str | None = None, limit: int = 50) -> Iterable[FetchResult]:
        yield self.fetch_topics(cursor=start_cursor, limit=limit)
