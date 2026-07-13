"""Tests for the query layer (GraphRetriever / BM25 / registry / CLI shape)."""

from __future__ import annotations

from pathlib import Path

import pytest

from kbforge.config import KbForgeConfig, PathsConfig
from kbforge.core import run
from kbforge.core.query import (
    BM25,
    GraphRetriever,
    EmbeddingRetriever,
    PageText,
    RetrieverContext,
    RETRIEVERS,
    tokenize,
    query_wiki,
)
from kbforge.core.query.base import Retriever
from kbforge.tools import make_fixtures


def _build_wiki(tmp_path: Path) -> Path:
    kb = tmp_path / "kb"
    make_fixtures.generate(kb)
    cfg = KbForgeConfig(root=kb, paths=PathsConfig())
    run(cfg)
    return kb / "wiki"


def test_tokenize_bigram():
    toks = tokenize("RAG 评测准确率")
    assert "rag" in toks
    assert "评测" in toks
    assert "测准" in toks  # bigram
    assert "准确" in toks  # bigram (not "准确率")
    # ascii run kept whole
    assert "bert" in tokenize("BERT model")


def test_registry_has_backends():
    assert "graph" in RETRIEVERS
    assert "embedding" in RETRIEVERS
    assert issubclass(GraphRetriever, Retriever)


def test_graph_retriever_ranks_relevant(tmp_path):
    wiki = _build_wiki(tmp_path)
    # "召回率" appears only in t101 -> unambiguous top hit
    hit = query_wiki(wiki, "召回率", top_k=3)
    assert hit and hit[0].id == "t101-rag-eval"
    # "RAG 评测" matches t101 and t103; PPR pulls the linked pair together
    results = query_wiki(wiki, "RAG 评测", top_k=3)
    assert results, "expected hits"
    ids = {r.id for r in results}
    assert "t101-rag-eval" in ids
    assert "t103-gpu-cost" in ids  # linked from t101, pulled in by PPR


def test_bm25_fallback_when_no_edges():
    ctx = RetrieverContext(
        pages=[
            PageText(
                id="x",
                title="x",
                type="post",
                body="长上下文直接丢给大模型会爆 GPU 成本",
                path="x.md",
            )
        ],
        edges=[],
        id_to_index={"x": 0},
    )
    res = GraphRetriever().retrieve("GPU 成本", top_k=1, ctx=ctx)
    assert res and res[0].id == "x"


def test_embedding_retriever_raises_when_unconfigured():
    retr = EmbeddingRetriever()
    ctx = RetrieverContext(pages=[], edges=[], id_to_index={})
    with pytest.raises(RuntimeError):
        retr.retrieve("anything", 1, ctx)


def test_query_wiki_context_shape(tmp_path):
    wiki = _build_wiki(tmp_path)
    ctx = RetrieverContext.from_wiki_dir(wiki)
    assert len(ctx.pages) == 3
    # t101->t102, t101->t103, t102->t103 (t103->t101 is a dup undirected)
    assert len(ctx.edges) == 3
    assert ("t101-rag-eval", "t102-chunk-strategy") in ctx.edges


def test_bm25_scorer_basic():
    docs = [tokenize("rag 评测 准确率"), tokenize("gpu 成本 控制")]
    bm25 = BM25(docs)
    # query term present only in doc 0
    s0 = bm25.score(tokenize("评测"), 0)
    s1 = bm25.score(tokenize("评测"), 1)
    assert s0 > 0
    assert s1 == 0
