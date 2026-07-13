"""Unit tests for the mechanical ingest layer (§5.3.1 content_hash)."""

from __future__ import annotations

from kbforge.core.wiki.ingest import content_hash, ingest_post

RESERVED = {"index.md", "log.md"}


def test_content_hash_is_deterministic() -> None:
    assert content_hash("a  b\nc") == content_hash("a b c")


def test_content_hash_ignores_only_whitespace_changes() -> None:
    assert content_hash("hello world") == content_hash("hello   world")


def test_ingest_preserves_type_and_body_links(sample_kb) -> None:
    post = ingest_post(sample_kb / "archive" / "2026" / "07" / "t101-rag-eval.md")
    assert post.meta["type"] == "case"
    assert post.meta["content_hash"].startswith("sha256:")
    assert "[[t102-chunk-strategy]]" in post.body
    # body-only hash is stored, not a hash of the whole file
    assert "topic_id" not in post.meta["content_hash"]
