"""Claim-level source enrichment (local-first, LLM optional).

The MVP ships a *local* claim extractor: deterministic, zero dependencies. It
splits each wiki page into candidate claims (sentences) and attaches the page's
source anchor (its ``sources`` frontmatter + slug), so a downstream RAG retriever
can cite *which source post a claim came from* — not just which page.

A real ``llm`` strategy is shipped and **OFF by default**: it calls an
OpenAI-compatible endpoint with only stdlib (``urllib``), and on any failure
(no key, network error, bad response) it transparently falls back to the local
extractor — so the product never breaks when an LLM is unavailable, and no
external SDK is required.
"""

from __future__ import annotations

import json
import os
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


class LLMEnrichmentStrategy(EnrichmentStrategy):
    """Optional LLM enhancement (OpenAI-compatible, stdlib only).

    Asks the model to return a JSON array of concise, self-contained claims
    extracted from the page. On missing key, network error, or unparseable
    response it transparently falls back to :class:`LocalClaimExtractor`, so the
    product never breaks when an LLM is unavailable. No external SDK, no required
    dependency.

    Mirror of :class:`kbforge.core.classify.LLMClassifier` — the same pattern is
    reused so both optional LLM features stay consistent and key-free by default.
    """

    def __init__(self, llm: dict | None = None, fallback: EnrichmentStrategy | None = None):
        self.llm = llm or {}
        self.fallback = fallback or LocalClaimExtractor()

    def extract(
        self, slug: str, title: str, body: str, sources: list[str]
    ) -> list[Claim]:
        api_key = self.llm.get("api_key") or os.getenv("LLM_API_KEY", "")
        if not api_key:
            return self.fallback.extract(slug, title, body, sources)
        try:
            return self._call(slug, title, body, sources)
        except Exception:
            return self.fallback.extract(slug, title, body, sources)

    def _call(
        self, slug: str, title: str, body: str, sources: list[str]
    ) -> list[Claim]:
        api_key = self.llm.get("api_key") or os.getenv("LLM_API_KEY", "")
        base = self.llm.get(
            "base_url", "https://api.openai.com/v1/chat/completions"
        )
        model = self.llm.get("model", "gpt-4o-mini")
        anchor = sources[0] if sources else None
        prompt = (
            "You are a knowledge-base claim extractor. From the page below, "
            "extract up to 12 concise, self-contained factual claims a reader "
            "would want to cite. Return ONLY a JSON array of strings, e.g. "
            '["claim one", "claim two"]. No prose, no markdown fences.\n\n'
            f"Title: {title}\n\nBody:\n{body[:4000]}"
        )
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        }
        data = _post_chat_completion(base, payload, api_key)
        content = data["choices"][0]["message"]["content"].strip()
        # Tolerate ```json ... ``` fences if the model adds them.
        if content.startswith("```"):
            content = content.strip("`")
            if content.lower().startswith("json"):
                content = content[4:]
            content = content.strip()
        items = json.loads(content)
        claims: list[Claim] = []
        for text in items:
            text = str(text).strip()
            if not text:
                continue
            claims.append(
                Claim(
                    text=text,
                    char_start=0,
                    char_end=len(text),
                    source_anchor=anchor,
                    slug=slug,
                )
            )
        return claims


def _post_chat_completion(url: str, payload: dict, api_key: str, timeout: int = 30) -> dict:
    """Call an OpenAI-compatible ``/chat/completions`` endpoint (stdlib only).

    Isolated so tests can patch this single network boundary. Raises on any
    transport/parse error — callers are expected to fall back gracefully.
    """
    import json
    import urllib.request

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


STRATEGIES: dict[str, type[EnrichmentStrategy]] = {
    "none": NoOpStrategy,
    "local": LocalClaimExtractor,
    "llm": LLMEnrichmentStrategy,
}


def get_strategy(
    name: str, llm: dict | None = None
) -> EnrichmentStrategy:
    """Resolve a strategy by name. ``llm`` receives its config (api_key etc.)."""
    if name not in STRATEGIES:
        raise ValueError(
            f"Unknown enrichment strategy '{name}'. Available: {sorted(STRATEGIES)}"
        )
    if name == "llm":
        return LLMEnrichmentStrategy(llm=llm or {})
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
