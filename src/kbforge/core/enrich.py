"""Claim-level source enrichment (local-first, LLM optional).

The MVP ships a *local* claim extractor: deterministic, zero dependencies. It
splits each wiki page into candidate claims (sentences) and attaches the page's
source anchor (its ``sources`` frontmatter + slug), so a downstream RAG retriever
can cite *which source post a claim came from* — not just which page.

An LLM-based strategy is a **documented extension point and OFF by default**,
mirroring ``EmbeddingRetriever``: the interface exists, a no-op default runs
with no external services, and a real LLM strategy can be dropped in later
without touching the pipeline.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from pathlib import Path

from .frontmatter import parse

_RESERVED = {"index.md", "log.md"}

_SENT_RE = re.compile(r"[^。！？!?\n]+[。！？!?]?")
_MIN_LEN = 12
_MAX_LEN = 400
_DEF_CUES = re.compile(r"(是|指|即|定义|称为|表示|意味|例如|比如|包括|优于|低于|高于|达到|约|≈|±)")


@dataclass
class Claim:
    """A candidate claim extracted from a wiki page, with its source anchor."""

    text: str
    char_start: int
    char_end: int
    source_anchor: str | None
    slug: str
    score: float = 1.0

    def to_dict(self) -> dict:
        return asdict(self)


class EnrichmentStrategy(ABC):
    """Strategy for turning a page body into structured claims."""

    @abstractmethod
    def extract(
        self, slug: str, title: str, body: str, sources: list[str]
    ) -> list[Claim]:
        ...


class NoOpStrategy(EnrichmentStrategy):
    """Default: extract nothing. The zero-dependency safe baseline."""

    def extract(self, slug, title, body, sources):
        return []


class LocalClaimExtractor(EnrichmentStrategy):
    """Deterministic, zero-dep sentence/claim splitter.

    Keeps a sentence as a candidate claim when it carries a *claim signal*:
    a wiki-link, a number/metric, a definition cue, or sufficient length.
    This is intentionally heuristic — it scopes candidate claims for a later
    (optional) LLM pass to refine, without requiring one.
    """

    def extract(
        self, slug: str, title: str, body: str, sources: list[str]
    ) -> list[Claim]:
        anchor = sources[0] if sources else None
        claims: list[Claim] = []
        for m in _SENT_RE.finditer(body):
            seg = m.group(0).strip()
            if not seg:
                continue
            if not (_MIN_LEN <= len(seg) <= _MAX_LEN):
                continue
            if not self._is_claim(seg):
                continue
            claims.append(
                Claim(
                    text=seg,
                    char_start=m.start(),
                    char_end=m.end(),
                    source_anchor=anchor,
                    slug=slug,
                )
            )
        return claims

    @staticmethod
    def _is_claim(seg: str) -> bool:
        if "[[" in seg:
            return True
        if re.search(r"\d", seg):
            return True
        if _DEF_CUES.search(seg):
            return True
        if len(seg) >= 28:
            return True
        return False


# Optional LLM strategy — extension point, intentionally OFF by default.
#
# class LLMEnrichmentStrategy(EnrichmentStrategy):
#     """Requires an LLM client injected via config; not wired into MVP.
#     Implement `extract` to call your model and return Claim objects.
#     Activate by registering it and selecting it from config.query.enrich."""
#     ...


STRATEGIES: dict[str, type[EnrichmentStrategy]] = {
    "none": NoOpStrategy,
    "local": LocalClaimExtractor,
}


def get_strategy(name: str) -> EnrichmentStrategy:
    if name not in STRATEGIES:
        raise ValueError(
            f"Unknown enrichment strategy '{name}'. Available: {sorted(STRATEGIES)}"
        )
    return STRATEGIES[name]()


def enrich_wiki(
    wiki_dir: Path, strategy: EnrichmentStrategy | None = None
) -> dict[str, list[dict]]:
    """Extract claims from every wiki page. Returns ``slug -> [claim dict]``."""
    strategy = strategy or NoOpStrategy()
    wiki_dir = Path(wiki_dir)
    out: dict[str, list[dict]] = {}
    for md in sorted(wiki_dir.glob("*.md")):
        if md.name in _RESERVED:
            continue
        meta, body = parse(md.read_text(encoding="utf-8"))
        slug = md.stem
        sources = meta.get("sources", []) or []
        claims = strategy.extract(slug, meta.get("title", slug), body, sources)
        if claims:
            out[slug] = [c.to_dict() for c in claims]
    return out
