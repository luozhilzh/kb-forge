"""Skeleton for adding a new platform adapter (WeChat / 微信公众号, etc.).

This is documentation-as-code, NOT a working implementation — it has no real
backend and is excluded from tests. Copy it, fill in the TODOs, register the
class in ``adapters/__init__.py`` (``ADAPTERS["wechat"] = WechatAdapter``), and
document the setup in ``docs/guide.md#新增平台``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from .base import Attachment, FetchResult, PlatformAdapter, Topic


class WechatAdapter(PlatformAdapter):
    def __init__(self, group_id: str, api_key: str = "") -> None:
        # TODO: replace with real credentials/config from KbForgeConfig.
        self.group_id = group_id
        self.api_key = api_key

    def fetch_topics(self, cursor: str | None = None, limit: int = 50) -> FetchResult:
        # TODO: call the WeChat API / parser and map results to Topic.
        raise NotImplementedError("WechatAdapter is a skeleton — implement fetch_topics().")

    def download_attachment(self, att: Attachment, dest: Path) -> Path:
        # TODO: download logic.
        raise NotImplementedError("WechatAdapter is a skeleton — implement download_attachment().")

    def paginate(self, start_cursor: str | None = None, limit: int = 50) -> Iterable[FetchResult]:
        # TODO: iterate pages using the cursor returned by fetch_topics().
        raise NotImplementedError("WechatAdapter is a skeleton — implement paginate().")
