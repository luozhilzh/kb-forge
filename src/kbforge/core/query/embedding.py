"""EmbeddingRetriever: optional, OFF by default (§5.3.2 / §12-②).

kb-forge does **not** bundle any model or vector store (local-zero-dependency
principle). This backend exists as a registered, lazy-loadable extension point:
it only does real work when the caller supplies an ``embedder`` and
``vector_store`` (e.g. via config/env in a downstream deployment). CI never
constructs it with real deps, so the import graph stays clean.
"""

from __future__ import annotations

from .base import Retriever, Result, RetrieverContext


class EmbeddingRetriever(Retriever):
    def __init__(self, embedder=None, vector_store=None):
        self.embedder = embedder
        self.vector_store = vector_store

    def retrieve(self, query: str, top_k: int, ctx: RetrieverContext) -> list[Result]:
        if self.embedder is None or self.vector_store is None:
            raise RuntimeError(
                "embedding 后端未配置：kb-forge 不内置任何模型或向量库。\n"
                "请在部署侧通过 config/env 提供自备 embedder 与 vector_store，\n"
                "并以 query.backend=embedding 调用。"
            )
        # Extension point: embed `query`, search `vector_store` over ctx.pages,
        # return sorted Result list. Left unimplemented by design (OFF).
        raise NotImplementedError(
            "EmbeddingRetriever 是可选扩展点；当前为 OFF 占位，需部署侧注入依赖后实现。"
        )
