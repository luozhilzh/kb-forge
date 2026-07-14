"""Tests for the enrich module (claim extraction + LLM strategy wiring)."""

import json
from unittest.mock import patch

from kbforge.core.enrich import (
    Claim,
    LLMEnrichmentStrategy,
    LocalClaimExtractor,
    NoOpStrategy,
    get_strategy,
)


def _meta_body():
    return {
        "title": "RAG 是什么",
        "sources": ["2025-02-27-t1525814582145582"],
    }, (
        "RAG 是检索增强生成。\n"
        "它把外部知识库检索结果喂给大模型以提升准确率，准确率达到 92%。\n"
        "定义：RAG 由检索器与生成器两部分组成。\n"
        "例如企业知识库问答是典型场景。\n"
    )


def test_noop_returns_empty():
    s = NoOpStrategy()
    claims = s.extract("s", "t", "任何正文都返回空", [])
    assert claims == []


def test_local_extracts_claims_with_signals():
    meta, body = _meta_body()
    claims = LocalClaimExtractor().extract(
        "slug1", meta["title"], body, meta["sources"]
    )
    # definition cue + number should yield at least one candidate claim
    assert len(claims) >= 1
    assert all(isinstance(c, Claim) for c in claims)
    # source anchor is carried through
    assert claims[0].source_anchor == meta["sources"][0]
    assert all(c.slug == "slug1" for c in claims)


def test_get_strategy_unknown_raises():
    import pytest

    with pytest.raises(ValueError):
        get_strategy("bogus")


def test_llm_without_key_falls_back_to_local():
    meta, body = _meta_body()
    strat = LLMEnrichmentStrategy(llm={}, fallback=LocalClaimExtractor())
    with patch("kbforge.core.enrich._post_chat_completion") as mock_post, patch(
        "kbforge.core.enrich.os.getenv", return_value=""
    ):
        claims = strat.extract("slug", meta["title"], body, meta["sources"])
    # the network boundary must NOT be touched when there is no key
    mock_post.assert_not_called()
    # falls back to local extraction
    assert len(claims) >= 1
    assert all(c.slug == "slug" for c in claims)


def _fake_completion(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}]}


def test_llm_with_key_calls_endpoint_and_parses():
    meta, body = _meta_body()
    completion = _fake_completion('["RAG 提升问答准确率", "企业知识库是典型场景"]')
    strat = LLMEnrichmentStrategy(
        llm={"api_key": "sk-test", "model": "gpt-4o-mini"},
        fallback=LocalClaimExtractor(),
    )
    with patch(
        "kbforge.core.enrich._post_chat_completion", return_value=completion
    ) as mock_post:
        claims = strat.extract("slug", meta["title"], body, meta["sources"])

    mock_post.assert_called_once()
    assert len(claims) == 2
    texts = {c.text for c in claims}
    assert "RAG 提升问答准确率" in texts
    assert "企业知识库是典型场景" in texts
    assert all(c.source_anchor == meta["sources"][0] for c in claims)


def test_llm_with_key_but_network_error_falls_back():
    meta, body = _meta_body()
    strat = LLMEnrichmentStrategy(
        llm={"api_key": "sk-test"}, fallback=LocalClaimExtractor()
    )
    with patch(
        "kbforge.core.enrich._post_chat_completion", side_effect=RuntimeError("boom")
    ) as mock_post:
        claims = strat.extract("slug", meta["title"], body, meta["sources"])
    mock_post.assert_called_once()
    # transparent fallback to local extraction
    assert len(claims) >= 1
    assert all(c.slug == "slug" for c in claims)


def test_get_strategy_llm_returns_llm_strategy():
    strat = get_strategy("llm", llm={"api_key": "sk-test"})
    assert isinstance(strat, LLMEnrichmentStrategy)


def test_llm_tolerates_json_fence():
    meta, body = _meta_body()
    completion = _fake_completion("```json\n[\"claim a\", \"claim b\"]\n```")
    strat = LLMEnrichmentStrategy(llm={"api_key": "sk-test"})
    with patch(
        "kbforge.core.enrich._post_chat_completion", return_value=completion
    ):
        claims = strat.extract("slug", meta["title"], body, meta["sources"])
    assert {c.text for c in claims} == {"claim a", "claim b"}
