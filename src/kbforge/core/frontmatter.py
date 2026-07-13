"""Tiny frontmatter (YAML + Markdown) helper. Avoids an extra dependency."""

from __future__ import annotations

import re
from typing import Any

import yaml

_FM_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)


def parse(text: str) -> tuple[dict[str, Any], str]:
    """Return (metadata dict, body string). Tolerates missing frontmatter."""
    m = _FM_RE.match(text)
    if not m:
        return {}, text
    meta = yaml.safe_load(m.group(1)) or {}
    if not isinstance(meta, dict):
        meta = {}
    return meta, m.group(2)


def dump(meta: dict[str, Any], body: str) -> str:
    """Serialize (metadata, body) back to a frontmatter document."""
    head = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False).strip()
    return f"---\n{head}\n---\n\n{body}"
