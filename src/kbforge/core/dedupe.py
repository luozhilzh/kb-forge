"""Cross-source duplicate detection (local-first, non-destructive by default).

kb-forge computes a body-only ``content_hash`` (sha256) for every page. This
module groups pages by that hash and, for each collision, marks the redundant
pages with a ``duplicate_of`` field pointing at a canonical page — without
touching the page body. It is the "dedupe" stage of the ingest pipeline
(``ingest → dedupe → wiki → …``) and works on **any** directory of Markdown
pages (archive posts, compiled wiki pages, or a mixed bundle), scanned
recursively.

Why this matters for a *reusable* product
-----------------------------------------
A knowledge base pulled from a platform like 知识星球 is full of repeats: the
same post re-shared, a thread cross-posted to another group, or two captures of
one source. Without dedupe, ``export``/``site``/``query`` all surface the
duplicates and inflate the corpus. Marking them (rather than deleting) keeps the
product safe for *anyone's* data while still letting consumers collapse groups.

Design — local-first, zero-dependency
-------------------------------------
* The default strategy ``mark`` is deterministic and needs no API key. Every
  page is **kept**; redundant pages get a ``duplicate_of: <canonical-slug>``
  field and every page gets a ``content_hash`` (filled in if missing). This is
  non-destructive: it only appends/updates frontmatter metadata, never edits
  the body or removes files.
* The canonical page of a collision is chosen deterministically: earliest
  ``published_at``, tie-broken by slug (so reruns are stable).
* A ``merge`` strategy (physically collapsing / relocating duplicates) is a
  **documented, OFF-by-default extension point** — useful when a caller wants to
  shrink a corpus, but risky for user data, so it is not wired into the MVP.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

from .frontmatter import parse

# Files that are not content pages and must never be scanned/rewritten.
_RESERVED = {"index.md", "log.md", "SCHEMA.md"}

# Same body-only normalization as ``core/wiki/ingest.content_hash`` so a hash
# computed here matches one computed during ingest (enables cross-layer dedup).
def content_hash(body: str) -> str:
    """sha256 over normalized body text (whitespace collapsed, stripped)."""
    normalized = re.sub(r"\s+", " ", body).strip()
    return "sha256:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _select_canonical(items: list[tuple[str, dict]]) -> str:
    """Pick the canonical slug from a collision group.

    Earliest ``published_at`` wins; ties broken by slug for determinism.
    """
    def key(item: tuple[str, dict]):
        slug, meta = item
        published = str(meta.get("published_at") or "")
        return (published or "9999", slug)

    return min(items, key=key)[0]


def _upsert_field(text: str, key: str, value: str) -> str:
    """Insert or replace a single ``key: value`` line inside the frontmatter.

    Operates only within the leading ``---`` block and preserves every other
    line (body, order, other fields). Returns the text unchanged if there is no
    frontmatter fence.
    """
    lines = text.split("\n")
    if not lines or lines[0] != "---":
        return text
    end = None
    for i in range(1, len(lines)):
        if lines[i] == "---":
            end = i
            break
    if end is None:
        return text
    fm = lines[1:end]
    for j, line in enumerate(fm):
        if re.match(rf"^{re.escape(key)}:", line):
            fm[j] = f"{key}: {value}"
            lines[1:end] = fm
            return "\n".join(lines)
    # Not present → append before the closing fence.
    fm.append(f"{key}: {value}")
    lines[1:end] = fm
    return "\n".join(lines)


@dataclass
class DedupeReport:
    """What ``dedupe_pages`` did (or would do under ``dry_run``)."""

    total: int = 0
    unique: int = 0
    duplicate_groups: int = 0
    duplicates: int = 0  # number of non-canonical (redundant) pages
    to_write: int = 0  # files that would be / were rewritten
    groups: list[dict] = field(default_factory=list)  # {hash, canonical, members}

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "unique": self.unique,
            "duplicate_groups": self.duplicate_groups,
            "duplicates": self.duplicates,
            "to_write": self.to_write,
            "groups": self.groups,
        }


# Strategy registry. ``mark`` ships; ``merge`` is an extension point (see module
# docstring) intentionally left out of the MVP so callers never lose data.
STRATEGIES = {"mark"}


def dedupe_pages(
    pages_dir: Path,
    *,
    strategy_name: str = "mark",
    dry_run: bool = False,
) -> DedupeReport:
    """Detect and mark duplicate pages under ``pages_dir`` (recursive).

    Groups every ``*.md`` page (except reserved files) by its body-only
    ``content_hash``. For collisions, the canonical page is chosen by
    :func:`_select_canonical` and every other member is annotated with
    ``duplicate_of``. Every page also gets a ``content_hash`` field (filled in
    if missing). When not ``dry_run``, the annotated files are written back
    in place (frontmatter metadata only — bodies are never edited).

    Returns a :class:`DedupeReport` describing the result.
    """
    if strategy_name not in STRATEGIES:
        raise ValueError(
            f"Unknown dedupe strategy '{strategy_name}'. Available: {sorted(STRATEGIES)}"
        )

    pages_dir = Path(pages_dir)
    files = [p for p in sorted(pages_dir.rglob("*.md")) if p.name not in _RESERVED]

    parsed: list[tuple[Path, str, dict, str, str, str]] = []
    for p in files:
        text = p.read_text(encoding="utf-8")
        meta, body = parse(text)
        h = str(meta.get("content_hash") or content_hash(body))
        parsed.append((p, p.stem, meta, body, text, h))

    by_hash: dict[str, list] = {}
    for item in parsed:
        by_hash.setdefault(item[5], []).append(item)

    report = DedupeReport(total=len(parsed))
    writes: list[tuple[Path, str]] = []

    for h, items in by_hash.items():
        members = [it[1] for it in items]
        if len(items) == 1:
            report.unique += 1
            p, slug, meta, _body, text, _ = items[0]
            if not meta.get("content_hash"):
                new_text = _upsert_field(text, "content_hash", h)
                if new_text != text:
                    writes.append((p, new_text))
                    report.to_write += 1
            report.groups.append({"hash": h, "canonical": slug, "members": members})
            continue

        # Collision → mark duplicates.
        report.duplicate_groups += 1
        report.duplicates += len(items) - 1
        canonical = _select_canonical([(it[1], it[2]) for it in items])
        report.groups.append(
            {"hash": h, "canonical": canonical, "members": members}
        )
        for p, slug, meta, _body, text, _ in items:
            new_text = text
            if not meta.get("content_hash"):
                new_text = _upsert_field(new_text, "content_hash", h)
            if slug != canonical:
                new_text = _upsert_field(new_text, "duplicate_of", canonical)
            if new_text != text:
                writes.append((p, new_text))
                report.to_write += 1

    if not dry_run:
        for p, new_text in writes:
            p.write_text(new_text, encoding="utf-8")

    return report
