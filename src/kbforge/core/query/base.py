"""Retriever contracts for kb-forge query layer.

Defines the backend-agnostic :class:`Retriever` interface, the serializable
:class:`Result` (kept MCP-friendly — see §5.7 / §12-④), and a
:class:`RetrieverContext` built from a compiled wiki dir. Backend classes
(GraphRetriever, EmbeddingRetriever) register themselves into ``RETRIEVERS``.

Design (§5.3.2):
  * ``GraphRetriever``   — Personalized PageRank over the ``[[wiki-link]]`` graph,
                           zero embedding cost, deterministic. MVP default.
  * ``EmbeddingRetriever`` — optional, OFF by default; lazy-loads a user-supplied
                           embedder + vector store. CI never touches it.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ..frontmatter import parse

_RESERVED = {"index.md", "log.md"}


@dataclass
class Result:
    """A single retrieved hit. Fully serializable (MCP-friendly)."""

    id: str
    score: float
    snippet: str
    source_path: str | None = None
    link: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PageText:
    id: str
    title: str
    type: str
    body: str
    path: str


@dataclass
class RetrieverContext:
    """Everything a retriever needs: page texts + the (undirected) link graph."""

    pages: list[PageText]
    edges: list[tuple[str, str]]  # undirected, de-duplicated (u, v) with u < v
    id_to_index: dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_wiki_dir(cls, wiki_dir: Path) -> "RetrieverContext":
        """Build context from a compiled wiki dir.

        Reads ``.graph.json`` for the edge list and each non-reserved ``*.md``
        for body/title. Dangling links (target not a known page) are dropped.
        """
        wiki_dir = Path(wiki_dir)
        graph_path = wiki_dir / ".graph.json"
        edges_raw: list = []
        if graph_path.exists():
            graph = json.loads(graph_path.read_text(encoding="utf-8"))
            edges_raw = graph.get("edges", [])

        pages: list[PageText] = []
        for md in sorted(wiki_dir.glob("*.md")):
            if md.name in _RESERVED:
                continue
            meta, body = parse(md.read_text(encoding="utf-8"))
            slug = md.stem
            pages.append(
                PageText(
                    id=slug,
                    title=meta.get("title", slug),
                    type=meta.get("type", "unknown"),
                    body=body,
                    path=str(md),
                )
            )

        id_to_index = {p.id: i for i, p in enumerate(pages)}
        edges: list[tuple[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for e in edges_raw:
            if isinstance(e, (list, tuple)) and len(e) == 2:
                u, v = str(e[0]), str(e[1])
                if u in id_to_index and v in id_to_index:
                    key = (u, v) if u < v else (v, u)
                    if key not in seen:
                        seen.add(key)
                        edges.append(key)
        return cls(pages=pages, edges=edges, id_to_index=id_to_index)


class Retriever(ABC):
    """Backend-agnostic retriever. Subclasses implement :meth:`retrieve`."""

    @abstractmethod
    def retrieve(
        self, query: str, top_k: int, ctx: RetrieverContext
    ) -> list[Result]:
        ...


# --------------------------------------------------------------------------- #
# Backend registry (thin: a dict + a factory)
# --------------------------------------------------------------------------- #
RETRIEVERS: dict[str, type[Retriever]] = {}


def register(name: str, cls: type[Retriever]) -> None:
    RETRIEVERS[name] = cls


def get_retriever(name: str, **kwargs) -> Retriever:
    if name not in RETRIEVERS:
        raise ValueError(
            f"Unknown retriever backend '{name}'. Available: {sorted(RETRIEVERS)}"
        )
    return RETRIEVERS[name](**kwargs)
