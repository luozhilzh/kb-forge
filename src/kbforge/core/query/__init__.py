"""kb-forge query layer (retrieval / RAG readiness).

Exposes the backend-agnostic retriever API plus a convenience ``query_wiki``.
The MVP default is ``graph`` (Personalized PageRank, zero-dependency); the
``embedding`` backend is an OFF extension point.
"""

from __future__ import annotations

from pathlib import Path

from .base import (
    RETRIEVERS,
    PageText,
    Result,
    Retriever,
    RetrieverContext,
    get_retriever,
    register,
)
from .bm25 import BM25, tokenize
from .embedding import EmbeddingRetriever
from .graph import GraphRetriever

# Register built-in backends.
register("graph", GraphRetriever)
register("embedding", EmbeddingRetriever)

__all__ = [
    "RETRIEVERS",
    "PageText",
    "Result",
    "Retriever",
    "RetrieverContext",
    "get_retriever",
    "register",
    "BM25",
    "tokenize",
    "GraphRetriever",
    "EmbeddingRetriever",
    "query_wiki",
]


def query_wiki(
    wiki_dir: str | Path,
    query: str,
    top_k: int = 5,
    backend: str = "graph",
) -> list[Result]:
    """Convenience: build a context from a compiled wiki and retrieve."""
    ctx = RetrieverContext.from_wiki_dir(Path(wiki_dir))
    retriever = get_retriever(backend)
    return retriever.retrieve(query, top_k, ctx)
