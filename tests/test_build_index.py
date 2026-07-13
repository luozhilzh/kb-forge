"""Unit tests for the wiki index / graph builder (§5.3)."""

from __future__ import annotations

import json

from kbforge.core.wiki.build_index import build_index, extract_links


def test_extract_links() -> None:
    assert extract_links("see [[a]] and [[b]] here") == ["a", "b"]


def test_build_index_produces_graph(built_wiki) -> None:
    graph = json.loads((built_wiki / ".graph.json").read_text(encoding="utf-8"))
    ids = {n["id"] for n in graph["nodes"]}
    assert {"t101-rag-eval", "t102-chunk-strategy", "t103-gpu-cost"} <= ids
    edges = {tuple(e) for e in graph["edges"]}
    assert ("t101-rag-eval", "t102-chunk-strategy") in edges
    assert ("t101-rag-eval", "t103-gpu-cost") in edges


def test_index_md_reserved_file_present(built_wiki) -> None:
    assert (built_wiki / "index.md").exists()
