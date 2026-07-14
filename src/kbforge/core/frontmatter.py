"""Tiny frontmatter (YAML + Markdown) helper. Avoids an extra dependency."""

from __future__ import annotations

import re
from typing import Any

import yaml

_FM_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)

# Characters that are illegal as the first byte of a YAML plain scalar. Posts
# downloaded from a platform sometimes carry titles like "@caucy ..." or
# "#评论回复 ..." which are valid Markdown but break `yaml.safe_load` (the `@`
# raises ScannerError; the `#` is silently eaten as a comment). We quote any
# `key: <value>` line whose value starts with one of these so the value is
# preserved as a string instead of lost/crashing.
_PROTECT_INDICATORS = set("@#&*!?%-`")


def _protect_scalars(fm: str) -> str:
    """Quote `key: value` lines whose value starts with an illegal indicator.

    Only touches the offending lines; valid scalars, inline flow lists
    (``tags: [a, b]``), block sequences, and booleans/numbers are left intact.
    """
    out: list[str] = []
    for line in fm.split("\n"):
        m = re.match(r"^(\s*[\w/-]+):\s*(\S.*)$", line)
        if m and m.group(2)[0] in _PROTECT_INDICATORS:
            key, val = m.group(1), m.group(2)
            esc = val.replace("\\", "\\\\").replace('"', '\\"')
            out.append(f'{key}: "{esc}"')
        else:
            out.append(line)
    return "\n".join(out)


def parse(text: str) -> tuple[dict[str, Any], str]:
    """Return (metadata dict, body string). Tolerates missing frontmatter.

    Robust to platform-exported frontmatter whose scalar values start with a
    YAML-illegal indicator (e.g. a title beginning with ``@`` or ``#``).
    """
    m = _FM_RE.match(text)
    if not m:
        return {}, text
    meta = yaml.safe_load(_protect_scalars(m.group(1))) or {}
    if not isinstance(meta, dict):
        meta = {}
    return meta, m.group(2)


def dump(meta: dict[str, Any], body: str) -> str:
    """Serialize (metadata, body) back to a frontmatter document."""
    head = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False).strip()
    return f"---\n{head}\n---\n\n{body}"
