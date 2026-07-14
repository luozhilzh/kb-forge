"""Tests for core.dedupe — non-destructive duplicate detection."""

from __future__ import annotations

from pathlib import Path

from kbforge.core.dedupe import (
    DedupeReport,
    _select_canonical,
    _upsert_field,
    content_hash,
    dedupe_pages,
)

_SAME_BODY = "球主本人主要熟悉Python和C++，过去8年一直从事一级市场债权产品开发。\n\n这是正文第二段。"


def _page(name: str, body: str, *, title="T", published_at="2025-01-01", extra: dict | None = None) -> str:
    meta = {"title": title, "published_at": published_at}
    if extra:
        meta.update(extra)
    fm = "---\n" + "\n".join(f"{k}: {v}" for k, v in meta.items()) + "\n---\n\n" + body
    return fm


def test_content_hash_is_body_only_and_stable():
    a = content_hash("  hello   world  \n\n")
    b = content_hash("hello world")
    assert a == b
    assert a.startswith("sha256:")


def test_identical_pages_marked_duplicate_of_canonical(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text(_page("a", _SAME_BODY, title="A", published_at="2025-03-01"), encoding="utf-8")
    (tmp_path / "b.md").write_text(_page("b", _SAME_BODY, title="B", published_at="2025-04-01"), encoding="utf-8")

    report = dedupe_pages(tmp_path, dry_run=False)
    assert report.total == 2
    assert report.duplicate_groups == 1
    assert report.duplicates == 1

    b_meta = (tmp_path / "b.md").read_text(encoding="utf-8")
    assert "duplicate_of: a" in b_meta
    # canonical keeps its own body, no duplicate_of on itself
    a_meta = (tmp_path / "a.md").read_text(encoding="utf-8")
    assert "duplicate_of" not in a_meta
    assert "content_hash:" in a_meta


def test_different_bodies_no_duplicates(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text(_page("a", "正文甲", published_at="2025-01-01"), encoding="utf-8")
    (tmp_path / "b.md").write_text(_page("b", "正文乙完全不同", published_at="2025-01-02"), encoding="utf-8")
    report = dedupe_pages(tmp_path, dry_run=False)
    assert report.duplicate_groups == 0
    assert report.duplicates == 0


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text(_page("a", _SAME_BODY), encoding="utf-8")
    (tmp_path / "b.md").write_text(_page("b", _SAME_BODY), encoding="utf-8")
    before = {p.name: p.read_text(encoding="utf-8") for p in tmp_path.glob("*.md")}
    report = dedupe_pages(tmp_path, dry_run=True)
    assert report.duplicates == 1
    after = {p.name: p.read_text(encoding="utf-8") for p in tmp_path.glob("*.md")}
    assert before == after


def test_idempotent_rerun_writes_zero(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text(_page("a", _SAME_BODY, published_at="2025-01-01"), encoding="utf-8")
    (tmp_path / "b.md").write_text(_page("b", _SAME_BODY, published_at="2025-02-01"), encoding="utf-8")
    dedupe_pages(tmp_path, dry_run=False)
    report2 = dedupe_pages(tmp_path, dry_run=False)
    assert report2.to_write == 0  # already annotated → nothing changes


def test_canonical_picks_earliest_published(tmp_path: Path) -> None:
    items = [
        ("late", {"published_at": "2025-09-01"}),
        ("early", {"published_at": "2025-01-01"}),
        ("mid", {"published_at": "2025-05-01"}),
    ]
    assert _select_canonical(items) == "early"


def test_canonical_tiebreak_by_slug(tmp_path: Path) -> None:
    items = [
        ("zzz", {"published_at": ""}),
        ("aaa", {"published_at": ""}),
    ]
    assert _select_canonical(items) == "aaa"


def test_missing_content_hash_is_filled(tmp_path: Path) -> None:
    # No content_hash field at all → should be added.
    (tmp_path / "a.md").write_text(_page("a", "unique body one", published_at="2025-01-01"), encoding="utf-8")
    report = dedupe_pages(tmp_path, dry_run=False)
    text = (tmp_path / "a.md").read_text(encoding="utf-8")
    assert "content_hash:" in text
    assert report.to_write == 1  # only the missing field was added


def test_upsert_field_inserts_and_replaces():
    text = "---\ntitle: X\n---\n\nbody"
    out = _upsert_field(text, "duplicate_of", "canon")
    assert "duplicate_of: canon" in out
    out2 = _upsert_field(out, "duplicate_of", "other")
    assert "duplicate_of: other" in out2
    # still exactly one duplicate_of line
    assert out2.count("duplicate_of:") == 1


def test_reserved_files_skipped(tmp_path: Path) -> None:
    (tmp_path / "index.md").write_text(_page("index", _SAME_BODY), encoding="utf-8")
    (tmp_path / "a.md").write_text(_page("a", _SAME_BODY), encoding="utf-8")
    report = dedupe_pages(tmp_path, dry_run=False)
    # index.md must not be scanned → only 'a' present → no duplicate group
    assert report.duplicate_groups == 0
    idx = (tmp_path / "index.md").read_text(encoding="utf-8")
    assert "duplicate_of" not in idx


def test_recursive_scan(tmp_path: Path) -> None:
    sub = tmp_path / "2025" / "02"
    sub.mkdir(parents=True)
    (tmp_path / "a.md").write_text(_page("a", _SAME_BODY, published_at="2025-01-01"), encoding="utf-8")
    (sub / "b.md").write_text(_page("b", _SAME_BODY, published_at="2025-02-01"), encoding="utf-8")
    report = dedupe_pages(tmp_path, dry_run=False)
    assert report.duplicate_groups == 1
    assert report.duplicates == 1
    assert (sub / "b.md").read_text(encoding="utf-8").count("duplicate_of:") == 1


def test_report_to_dict_shape():
    r = DedupeReport(total=3, unique=1, duplicate_groups=1, duplicates=2, to_write=2)
    d = r.to_dict()
    assert set(d) == {"total", "unique", "duplicate_groups", "duplicates", "to_write", "groups"}
