"""Tests for local claim-level enrichment (core/enrich.py)."""

from pathlib import Path

import pytest

from kbforge.core.enrich import (
    Claim,
    EnrichmentStrategy,
    LocalClaimExtractor,
    NoOpStrategy,
    enrich_wiki,
    get_strategy,
)
from kbforge.core.frontmatter import dump


def _write(wiki: Path, slug: str, body: str, sources=None) -> None:
    meta = {
        "type": "concept",
        "title": slug,
        "content_hash": "h",
        "sources": sources or ["archive/2024/01/post-123.md"],
    }
    (wiki / f"{slug}.md").write_text(dump(meta, body), encoding="utf-8")


def test_noop_returns_empty(tmp_path: Path) -> None:
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    _write(wiki, "a", "这是一句很长的定义性内容，用来测试 noop 策略是否返回空字典。")
    assert enrich_wiki(wiki, strategy=NoOpStrategy()) == {}


def test_local_extractor_finds_claim_with_link(tmp_path: Path) -> None:
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    body = "第一段普通。分块策略能提升检索效果，详见[[t102-chunk-strategy]]。"
    _write(wiki, "a", body)
    out = enrich_wiki(wiki, strategy=LocalClaimExtractor())
    claims = out.get("a", [])
    assert any("t102-chunk-strategy" in c["text"] for c in claims)
    assert claims[0]["source_anchor"].endswith("post-123.md")
    assert claims[0]["slug"] == "a"


def test_local_extractor_skips_short(tmp_path: Path) -> None:
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    _write(wiki, "a", "短句。")
    out = enrich_wiki(wiki, strategy=LocalClaimExtractor())
    claims = out.get("a", [])
    assert all(len(c["text"]) >= 12 for c in claims)


def test_local_extractor_catches_metric(tmp_path: Path) -> None:
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    _write(wiki, "a", "GPU 推理成本约每小时 2.5 元，显著低于训练开销。")
    out = enrich_wiki(wiki, strategy=LocalClaimExtractor())
    assert out.get("a"), "metric sentence should be extracted as a claim"


def test_get_strategy_unknown_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        get_strategy("nope")


def test_enrich_wiki_dict_shape(tmp_path: Path) -> None:
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    _write(wiki, "a", "GPU 成本约 2.5 元每小时。检索召回率约 0.85。")
    out = enrich_wiki(wiki, strategy=LocalClaimExtractor())
    assert isinstance(out, dict)
    for claims in out.values():
        for c in claims:
            assert set(c.keys()) >= {
                "text",
                "source_anchor",
                "slug",
                "char_start",
                "char_end",
            }


def test_strategy_is_abstract() -> None:
    with pytest.raises(TypeError):
        EnrichmentStrategy()  # type: ignore[abstract]


def test_claim_serializable() -> None:
    c = Claim(text="x", char_start=0, char_end=1, source_anchor="s", slug="a")
    assert c.to_dict()["slug"] == "a"
