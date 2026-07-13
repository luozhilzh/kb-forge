"""GraphRetriever: Personalized PageRank over the wiki link graph.

Pipeline (§5.3.2, locked):
  1. Build an **undirected, uniformly-weighted** graph from ``[[wiki-link]]`` edges.
  2. Compute a **lexical seed distribution** via BM25 over page bodies.
  3. Run **Personalized PageRank** (damping α=0.85) as power iteration.
  4. Sparse fallback: if the graph has no edges, or BM25 scores nothing,
     rank by pure BM25 (and by graph degree if even that is empty) so we
     *always* return something.
"""

from __future__ import annotations

import re
from collections import Counter

from .base import Retriever, Result, RetrieverContext
from .bm25 import BM25, tokenize

DAMPING = 0.85
MAX_ITER = 100
CONVERGE = 1e-6
SNIPPET_LEN = 120


def _build_adj(ctx: RetrieverContext) -> tuple[list[list[int]], list[int]]:
    n = len(ctx.pages)
    adj: list[set[int]] = [set() for _ in range(n)]
    for u, v in ctx.edges:
        iu, iv = ctx.id_to_index[u], ctx.id_to_index[v]
        adj[iu].add(iv)
        adj[iv].add(iu)
    adj_lists = [sorted(s) for s in adj]
    deg = [len(a) for a in adj_lists]
    return adj_lists, deg


def _ppr(ctx: RetrieverContext, seed: list[float], alpha: float = DAMPING,
         max_iter: int = MAX_ITER, converge: float = CONVERGE) -> list[float]:
    """Power iteration of personalized PageRank with dangling-node redistribution."""
    n = len(ctx.pages)
    if n == 0:
        return []
    adj, deg = _build_adj(ctx)
    x = list(seed)
    for _ in range(max_iter):
        dangling_mass = sum(x[j] for j in range(n) if deg[j] == 0)
        new = [0.0] * n
        for i in range(n):
            s = 0.0
            for j in adj[i]:
                s += x[j] / deg[j]
            new[i] = (1.0 - alpha) * s + alpha * seed[i] + (1.0 - alpha) * dangling_mass / n
        diff = sum(abs(new[i] - x[i]) for i in range(n))
        x = new
        if diff < converge:
            break
    return x


def _snippet(body: str, q_tokens: list[str]) -> str:
    text = re.sub(r"\s+", " ", body).strip()
    low = text.lower()
    pos = -1
    for t in q_tokens:
        idx = low.find(t.lower())
        if idx >= 0:
            pos = idx
            break
    if pos < 0:
        return text[:SNIPPET_LEN]
    start = max(0, pos - 20)
    head = "…" if start > 0 else ""
    return head + text[start : start + SNIPPET_LEN]


class GraphRetriever(Retriever):
    def __init__(self, k1: float = 1.5, b: float = 0.75,
                 damping: float = DAMPING, max_iter: int = MAX_ITER):
        self.k1 = k1
        self.b = b
        self.damping = damping
        self.max_iter = max_iter

    def retrieve(self, query: str, top_k: int, ctx: RetrieverContext) -> list[Result]:
        n = len(ctx.pages)
        if n == 0:
            return []

        docs = [tokenize(p.body) for p in ctx.pages]
        bm25 = BM25(docs, self.k1, self.b)
        q_tokens = tokenize(query)
        raw = [bm25.score(q_tokens, i) for i in range(n)]
        total = sum(raw)

        if total <= 0 or len(ctx.edges) == 0:
            # Sparse/lexically-empty fallback: pure BM25 (or degree if all zero).
            if all(r == 0 for r in raw):
                _, deg = _build_adj(ctx)
                order = sorted(range(n), key=lambda i: deg[i], reverse=True)
                scores = [float(deg[i]) for i in range(n)]
            else:
                order = sorted(range(n), key=lambda i: raw[i], reverse=True)
                scores = raw
        else:
            seed = [r / total for r in raw]
            pr = _ppr(ctx, seed, self.damping, self.max_iter)
            order = sorted(range(n), key=lambda i: pr[i], reverse=True)
            scores = pr

        results: list[Result] = []
        for i in order[:top_k]:
            p = ctx.pages[i]
            results.append(
                Result(
                    id=p.id,
                    score=round(scores[i], 6),
                    snippet=_snippet(p.body, q_tokens),
                    source_path=p.path,
                    link=f"[[{p.id}]]",
                )
            )
        return results
