"""Platform adapter abstraction.

Every downstream stage depends only on this interface, so the pipeline is
decoupled from any single community platform. Implement
:class:`PlatformAdapter` for a new source (see ``example_wechat.py``).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


@dataclass
class Attachment:
    name: str
    url: str = ""
    size: int = 0


@dataclass
class Topic:
    """A single post as ingested from a platform."""

    topic_id: str
    title: str
    body: str
    published_at: str  # ISO-8601
    group_id: str
    author: str = ""
    attachments: list[Attachment] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class FetchResult:
    topics: list[Topic]
    next_cursor: str | None = None


class PlatformAdapter(ABC):
    """Interface every platform backend must implement."""

    @abstractmethod
    def fetch_topics(
        self, cursor: str | None = None, limit: int = 50
    ) -> FetchResult:
        """Return a page of topics. ``cursor`` is None for the first page."""

    @abstractmethod
    def download_attachment(self, att: Attachment, dest: Path) -> Path:
        """Download ``att`` into ``dest`` (which may be a directory). Return path."""

    @abstractmethod
    def paginate(
        self, start_cursor: str | None = None, limit: int = 50
    ) -> Iterable[FetchResult]:
        """Yield successive :class:`FetchResult` pages until exhausted."""
