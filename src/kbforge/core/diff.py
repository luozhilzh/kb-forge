"""OKF anti-drift guard + single-state validation.

Two public surfaces, both zero-dependency and deterministic:

* :func:`validate_wiki` — single-state OKF compliance check of a compiled wiki
  (every page must carry ``type`` + ``content_hash``; every ``[[wiki-link]]``
  must resolve to a known page). This is the contract gate.
* :func:`diff_wiki` — compare the current wiki against a saved baseline
  snapshot (created on first run), reporting added / removed / changed pages,
  broken links, orphaned references, and contract violations. Re-run it after
  every re-ingest to catch knowledge-base drift before it reaches RAG.

Snapshots are plain JSON (``.wiki_snapshot.json``) so no old wiki dir needs to
be retained. All report types expose ``to_dict()`` for MCP-friendly output.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .frontmatter import parse
from .wiki.build_index import extract_links

_RESERVED = {"index.md", "log.md"}
# Slugs that are valid link targets but never real pages.
_RESERVED_SLUGS = {"index", "log"}


def _link_target(inner: str) -> str:
    """Return the slug part of a ``[[slug|label]]`` / ``[[slug]]`` token."""
    return inner.split("|", 1)[0].strip()


# --------------------------------------------------------------------------- #
# Report shapes
# --------------------------------------------------------------------------- #
@dataclass
class Violation:
    """A single OKF contract violation on one page (or the wiki as a whole)."""

    slug: str
    kind: str  # e.g. "missing_type", "broken_link", "missing_content_hash"
    detail: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class WikiSnapshot:
    """A captured wiki state: ``slug -> page facts``."""

    pages: dict[str, dict]  # slug -> {type,title,content_hash,sources,links}

    def to_dict(self) -> dict:
        return {"pages": self.pages}

    def save(self, path: Path) -> None:
        Path(path).write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> "WikiSnapshot":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(pages=data.get("pages", {}))

    @classmethod
    def from_wiki_dir(cls, wiki_dir: Path) -> "WikiSnapshot":
        wiki_dir = Path(wiki_dir)
        pages: dict[str, dict] = {}
        for md in sorted(wiki_dir.glob("*.md")):
            if md.name in _RESERVED:
                continue
            meta, body = parse(md.read_text(encoding="utf-8"))
            slug = md.stem
            pages[slug] = {
                "type": meta.get("type"),
                "title": meta.get("title"),
                "content_hash": meta.get("content_hash"),
                "sources": meta.get("sources", []) or [],
                "links": extract_links(body),
            }
        return cls(pages=pages)


@dataclass
class DiffReport:
    """What changed between two wiki snapshots."""

    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    changed: dict[str, list[str]] = field(default_factory=dict)
    broken_links: dict[str, list[str]] = field(default_factory=dict)
    orphan_refs: list[str] = field(default_factory=list)
    contract_violations: list[Violation] = field(default_factory=list)
    baseline_created: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


# --------------------------------------------------------------------------- #
# Single-state validation
# --------------------------------------------------------------------------- #
def _validate_pages(pages: dict[str, dict]) -> list[Violation]:
    known = set(pages) | _RESERVED_SLUGS
    violations: list[Violation] = []
    for slug, st in pages.items():
        if not st.get("type"):
            violations.append(
                Violation(slug, "missing_type", "page has no `type` in frontmatter")
            )
        if not st.get("content_hash"):
            violations.append(
                Violation(
                    slug,
                    "missing_content_hash",
                    "page has no `content_hash`; re-ingest may have dropped it",
                )
            )
        for raw in st.get("links", []):
            target = _link_target(raw)
            if target and target not in known:
                violations.append(
                    Violation(
                        slug,
                        "broken_link",
                        f"links to [[{target}]] which is not a known page",
                    )
                )
    return violations


def validate_wiki(wiki_dir: Path) -> list[Violation]:
    """Validate a compiled wiki against the OKF contract. Returns violations."""
    snap = WikiSnapshot.from_wiki_dir(Path(wiki_dir))
    return _validate_pages(snap.pages)


# --------------------------------------------------------------------------- #
# Two-state diff
# --------------------------------------------------------------------------- #
def compare_snapshots(before: WikiSnapshot, after: WikiSnapshot) -> DiffReport:
    b_pages = before.pages
    a_pages = after.pages
    b_slugs = set(b_pages)
    a_slugs = set(a_pages)

    added = sorted(a_slugs - b_slugs)
    removed = sorted(b_slugs - a_slugs)

    changed: dict[str, list[str]] = {}
    for slug in sorted(b_slugs & a_slugs):
        b, a = b_pages[slug], a_pages[slug]
        diffs: list[str] = []
        if b.get("type") != a.get("type"):
            diffs.append(f"type: {b.get('type')!r} -> {a.get('type')!r}")
        if b.get("title") != a.get("title"):
            diffs.append(f"title: {b.get('title')!r} -> {a.get('title')!r}")
        if b.get("content_hash") != a.get("content_hash"):
            diffs.append("content_hash changed (body edited)")
        if b.get("sources") != a.get("sources"):
            diffs.append(f"sources: {b.get('sources')!r} -> {a.get('sources')!r}")
        if b.get("links") != a.get("links"):
            diffs.append("links changed")
        if diffs:
            changed[slug] = diffs

    # Broken links in `after`.
    a_known = a_slugs | _RESERVED_SLUGS
    broken_links: dict[str, list[str]] = {}
    for slug, st in a_pages.items():
        broken = [t for t in (_link_target(l) for l in st.get("links", []))
                  if t and t not in a_known]
        if broken:
            broken_links[slug] = broken

    # Orphan refs: targets that existed in `before` links but are missing now.
    before_targets: set[str] = set()
    for st in b_pages.values():
        for l in st.get("links", []):
            t = _link_target(l)
            if t:
                before_targets.add(t)
    orphan_refs = sorted(before_targets - a_slugs - _RESERVED_SLUGS)

    # Contract violations on `after`.
    contract_violations = _validate_pages(a_pages)

    return DiffReport(
        added=added,
        removed=removed,
        changed=changed,
        broken_links=broken_links,
        orphan_refs=orphan_refs,
        contract_violations=contract_violations,
    )


def diff_wiki(
    wiki_dir: Path,
    before_dir: Path | None = None,
    baseline_name: str = ".wiki_snapshot.json",
) -> DiffReport:
    """Compare the current wiki against a baseline.

    * If ``before_dir`` is given, compare against that wiki dir.
    * Otherwise, compare against ``<wiki_dir>/.wiki_snapshot.json``. On the
      first run (no snapshot yet) a baseline is created and a report with
      ``baseline_created=True`` is returned.

    The baseline is always refreshed to the current state after a comparison.
    """
    wiki_dir = Path(wiki_dir)
    after = WikiSnapshot.from_wiki_dir(wiki_dir)

    if before_dir is not None:
        before = WikiSnapshot.from_wiki_dir(Path(before_dir))
        report = compare_snapshots(before, after)
        after.save(wiki_dir / baseline_name)
        return report

    snap = wiki_dir / baseline_name
    if snap.exists():
        before = WikiSnapshot.load(snap)
        report = compare_snapshots(before, after)
        after.save(snap)
        return report

    after.save(snap)
    return DiffReport(baseline_created=True)
