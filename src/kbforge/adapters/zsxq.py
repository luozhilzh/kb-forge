"""Zsxq (知识星球) adapter — wraps the local ``zsxq-cli`` binary.

The CLI path is configurable (never hardcoded). Output is parsed as JSON.
This adapter requires a real login session and is excluded from CI; it is the
only place that touches the platform directly.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Iterable

from .base import Attachment, FetchResult, PlatformAdapter, Topic


class ZsxqAdapter(PlatformAdapter):
    def __init__(self, group_id: str, cli_path: str = "zsxq-cli") -> None:
        self.group_id = group_id
        self.cli_path = cli_path

    # ------------------------------------------------------------------ #
    def _run(self, *args: str) -> dict[str, Any]:
        if shutil.which(self.cli_path) is None:
            raise RuntimeError(
                f"zsxq-cli not found at '{self.cli_path}'. Install it and set "
                f"zsxq_cli_path in config, or use MockAdapter in tests."
            )
        cmd = [self.cli_path, "group", "+topics", "--group-id", self.group_id, *args]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise RuntimeError(f"zsxq-cli failed ({proc.returncode}): {proc.stderr.strip()}")
        return json.loads(proc.stdout)

    def _to_topic(self, raw: dict[str, Any]) -> Topic:
        # Field names are tolerant of minor CLI schema drift.
        tid = str(raw.get("topic_id") or raw.get("id") or "")
        attachments = [
            Attachment(name=a.get("name", ""), url=a.get("url", ""), size=a.get("size", 0))
            for a in raw.get("attachments", []) or []
        ]
        return Topic(
            topic_id=tid,
            title=raw.get("title", "") or (raw.get("talk") or {}).get("title", ""),
            body=raw.get("content", "") or raw.get("text", ""),
            published_at=raw.get("created_at", "") or raw.get("published_at", ""),
            group_id=self.group_id,
            author=raw.get("owner", {}).get("name", "") if raw.get("owner") else "",
            attachments=attachments,
            tags=raw.get("tags", []) or [],
            extra=raw,
        )

    # ------------------------------------------------------------------ #
    def fetch_topics(self, cursor: str | None = None, limit: int = 50) -> FetchResult:
        args = ["--limit", str(limit)]
        if cursor is not None:
            args += ["--end-time", cursor]  # backward pagination cursor
        payload = self._run(*args)
        topics = [self._to_topic(t) for t in payload.get("topics", [])]
        return FetchResult(topics, next_cursor=payload.get("next_end_time"))

    def download_attachment(self, att: Attachment, dest: Path) -> Path:
        dest_path = dest / att.name if dest.is_dir() else dest
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        # The exact download subcommand is verified at build time; this is the
        # expected shape. Fail loudly if the CLI contract changes.
        self._run("download", "--url", att.url, "--out", str(dest_path))
        return dest_path

    def paginate(self, start_cursor: str | None = None, limit: int = 50) -> Iterable[FetchResult]:
        cursor = start_cursor
        while True:
            result = self.fetch_topics(cursor=cursor, limit=limit)
            yield result
            if not result.topics or result.next_cursor is None:
                break
            cursor = result.next_cursor
