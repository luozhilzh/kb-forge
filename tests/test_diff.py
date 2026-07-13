"""Tests for the OKF anti-drift guard (core/diff.py)."""

from pathlib import Path

from kbforge.core.diff import (
    DiffReport,
    Violation,
    WikiSnapshot,
    compare_snapshots,
    diff_wiki,
    validate_wiki,
)
from kbforge.core.frontmatter import dump


def _page(slug: str, body: str, **meta) -> str:
    m = {
        "type": "concept",
        "title": slug,
        "content_hash": "h",
        "sources": ["archive/2024/01/post-1.md"],
        **meta,
    }
    return dump(m, body)


def _write(wiki: Path, slug: str, body: str, **meta) -> None:
    (wiki / f"{slug}.md").write_text(_page(slug, body, **meta), encoding="utf-8")


def test_validate_flags_missing_type(tmp_path: Path) -> None:
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    _write(wiki, "a", "body", type=None)
    violations = validate_wiki(wiki)
    assert any(v.kind == "missing_type" for v in violations)


def test_validate_flags_broken_link(tmp_path: Path) -> None:
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    _write(wiki, "a", "see [[ghost]] here")
    violations = validate_wiki(wiki)
    broken = [v for v in violations if v.kind == "broken_link"]
    assert broken and "ghost" in broken[0].detail


def test_validate_ok_when_links_resolve(tmp_path: Path) -> None:
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    _write(wiki, "a", "see [[b]]")
    _write(wiki, "b", "target")
    assert validate_wiki(wiki) == []


def test_snapshot_roundtrip(tmp_path: Path) -> None:
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    _write(wiki, "a", "links [[b]]")
    _write(wiki, "b", "x")
    snap = WikiSnapshot.from_wiki_dir(wiki)
    assert set(snap.pages) == {"a", "b"}
    p = tmp_path / "snap.json"
    snap.save(p)
    loaded = WikiSnapshot.load(p)
    assert loaded.pages == snap.pages


def test_compare_detects_added_removed_changed(tmp_path: Path) -> None:
    before = tmp_path / "before"
    before.mkdir()
    _write(before, "a", "v1", content_hash="h1")
    _write(before, "b", "to remove")
    after = tmp_path / "after"
    after.mkdir()
    _write(after, "a", "v2 edited", content_hash="h2")  # changed
    _write(after, "c", "new")  # added
    rep = compare_snapshots(
        WikiSnapshot.from_wiki_dir(before), WikiSnapshot.from_wiki_dir(after)
    )
    assert rep.added == ["c"]
    assert rep.removed == ["b"]
    assert "a" in rep.changed
    assert any("content_hash" in d for d in rep.changed["a"])


def test_diff_creates_baseline_then_detects_change(tmp_path: Path) -> None:
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    _write(wiki, "a", "original", content_hash="h1")
    rep1 = diff_wiki(wiki)
    assert rep1.baseline_created is True
    assert (wiki / ".wiki_snapshot.json").exists()

    _write(wiki, "a", "edited body", content_hash="h2")
    rep2 = diff_wiki(wiki)
    assert rep2.baseline_created is False
    assert "a" in rep2.changed


def test_diff_with_explicit_before(tmp_path: Path) -> None:
    before = tmp_path / "before"
    before.mkdir()
    _write(before, "a", "x", content_hash="h1")
    after = tmp_path / "after"
    after.mkdir()
    _write(after, "a", "y", content_hash="h2")
    rep = diff_wiki(after, before_dir=before)
    assert "a" in rep.changed
    assert any("content_hash" in d for d in rep.changed["a"])


def test_report_is_serializable(tmp_path: Path) -> None:
    rep = DiffReport(added=["x"], changed={"y": ["type changed"]})
    d = rep.to_dict()
    assert d["added"] == ["x"]
    assert d["changed"] == {"y": ["type changed"]}
    v = Violation("a", "broken_link", "detail")
    assert v.to_dict()["kind"] == "broken_link"
