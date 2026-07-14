"""Auto-classification of wiki pages into the OKF five-class structure.

This is the *structure* layer of kb-forge: it turns a flat pile of ingested
``post`` pages into a typed knowledge base (``concept / entity / case /
pitfall / scheme / comparison / post``) that the rest of the product — export,
site, query — can consume generically.

Design aligns with the project's **local-first, zero-dependency** principle:

* The default strategy ``local`` is deterministic and needs no API key. It
  scores each candidate type from (a) tag overlap with a configurable lexicon,
  (b) structural signals in the page headings, and (c) keyword density in the
  body. Anything with no signal stays ``post``.
* ``llm`` is an **optional enhancement**: it calls an OpenAI-compatible endpoint
  with only stdlib (``urllib``), and on any failure (no key, network error,
  bad response) it transparently falls back to ``local``. No external SDK, no
  required dependency.
* Both the type set and the lexicon / structural rules are **user-configurable**
  via ``config.yaml`` → ``classify:``. Nothing is hardcoded to one domain, so
  the product works for *anyone's* archive, not just this one.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from pathlib import Path

from ..classify_config import (
    DEFAULT_LEXICON,
    DEFAULT_STRUCTURAL_RULES,
    DEFAULT_TYPES,
    ClassifyConfig,
)
from .frontmatter import parse
from .wiki.build_index import build_index

_RESERVVED = {"index.md", "log.md"}

_TAG_SEP = re.compile(r"[/、,，|\s]+")


def _tag_matches(tag: str, cue: str) -> bool:
    """A tag cue matches only when it equals one *segment* of the tag.

    Tags are often compound (``业务落地``, ``大模型/训练``); a raw substring check
    would let ``模型`` wrongly match ``大模型``. Segment-exact matching keeps the
    lexicon precise and lets users map cues to their own tag vocabulary.
    """
    return cue.lower() in [s.lower() for s in _TAG_SEP.split(tag)]

# OKF default type set. ``post`` is the fallback for "no clear signal".
DEFAULT_TYPES = [
    "concept",
    "entity",
    "case",
    "pitfall",
    "scheme",
    "comparison",
    "post",
]

# Candidate types we actively score (``post`` is the fallback, not scored).
_SCORED = ["case", "pitfall", "scheme", "comparison", "concept", "entity"]

# Most-specific first → used as tie-breaker when scores tie.
_PRIORITY = ["case", "pitfall", "scheme", "comparison", "concept", "entity"]

# Body-keyword density is a *weak* signal. For ``entity`` it is disabled entirely:
# a post that merely *mentions* a tool/model is not an entity page — only an
# explicit title/heading/tag naming one counts.
_BODY_WEIGHT = {"entity": 0.0}


# --------------------------------------------------------------------------- #
# Strategies
# --------------------------------------------------------------------------- #
class ClassifierStrategy(ABC):
    @abstractmethod
    def classify(self, slug: str, title: str, tags: list[str], body: str) -> str:
        ...


class LocalClassifier(ClassifierStrategy):
    """Deterministic, zero-dependency scorer.

    For each candidate type, accumulate a score from three signals and pick the
    highest; ties broken by :data:`_PRIORITY`; zero signal → ``post``.
    """

    def __init__(self, cfg: ClassifyConfig):
        self.cfg = cfg
        # Pre-compile heading matchers per type.
        self._head_re: dict[str, re.Pattern] = {}
        for t, cues in cfg.structural_rules.items():
            if cues:
                self._head_re[t] = re.compile("|".join(re.escape(c) for c in cues))

    def classify(self, slug: str, title: str, tags: list[str], body: str) -> str:
        scores: dict[str, float] = {t: 0.0 for t in _SCORED}
        headings = [ln.strip("# ").strip() for ln in body.splitlines() if ln.startswith("## ")]

        for t in _SCORED:
            cues = self.cfg.lexicon.get(t, [])
            if not cues:
                continue
            # (a) tag overlap (segment-exact — see _tag_matches)
            for tag in tags:
                for cue in cues:
                    if cue and _tag_matches(tag, cue):
                        scores[t] += 2.0
            # (b) structural heading signal
            hr = self._head_re.get(t)
            if hr:
                for h in headings:
                    if hr.search(h):
                        scores[t] += 3.0
                        break
            # (c) keyword density in body (weak tiebreaker; entity disabled)
            bw = _BODY_WEIGHT.get(t, 1.0)
            if bw:
                low = body.lower()
                hits = 0
                for cue in cues:
                    cl = cue.lower()
                    if cl:
                        hits += low.count(cl)
                if hits:
                    scores[t] += bw
            # (d) title cue
            low_title = title.lower()
            for cue in cues:
                cl = cue.lower()
                if cl and cl in low_title:
                    scores[t] += 2.0
                    break

        best, best_score = "post", 0.0
        for t in _PRIORITY:  # iterate in priority order → ties favor specific types
            if scores[t] > best_score:
                best, best_score = t, scores[t]
        return best


class LLMClassifier(ClassifierStrategy):
    """Optional LLM enhancement (OpenAI-compatible, stdlib only).

    Falls back to ``local`` on missing key, network error, or unparseable
    response — so the product never breaks when LLM is unavailable.
    """

    def __init__(self, cfg: ClassifyConfig, fallback: ClassifierStrategy):
        self.cfg = cfg
        self.fallback = fallback

    def classify(self, slug: str, title: str, tags: list[str], body: str) -> str:
        api_key = (self.cfg.llm or {}).get("api_key")
        if not api_key:
            return self.fallback.classify(slug, title, tags, body)
        try:
            return self._call(slug, title, tags, body)
        except Exception:
            return self.fallback.classify(slug, title, tags, body)

    def _call(self, slug: str, title: str, tags: list[str], body: str) -> str:
        import json
        import urllib.request

        base = (self.cfg.llm or {}).get("base_url", "https://api.openai.com/v1/chat/completions")
        model = (self.cfg.llm or {}).get("model", "gpt-4o-mini")
        types = self.cfg.types
        prompt = (
            "You are a knowledge-base classifier. Given a page, respond with "
            "EXACTLY ONE of these type names and nothing else:\n"
            f"{', '.join(types)}\n\n"
            f"Title: {title}\nTags: {', '.join(tags)}\n"
            f"Body excerpt:\n{body[:2000]}"
        )
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        }
        req = urllib.request.Request(
            base,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp)
        text = data["choices"][0]["message"]["content"].strip().lower()
        for t in types:
            if t.lower() == text or t.lower() in text:
                return t
        # Unrecognized → fall back
        return self.fallback.classify(slug, title, tags, body)


STRATEGIES: dict[str, type[ClassifierStrategy]] = {
    "local": LocalClassifier,
    "llm": LLMClassifier,
}


def get_strategy(name: str, cfg: ClassifyConfig) -> ClassifierStrategy:
    if name not in STRATEGIES:
        raise ValueError(
            f"Unknown classify strategy '{name}'. Available: {sorted(STRATEGIES)}"
        )
    if name == "llm":
        return LLMClassifier(cfg, LocalClassifier(cfg))
    return LocalClassifier(cfg)


# --------------------------------------------------------------------------- #
# Wiki-level operation
# --------------------------------------------------------------------------- #
def _set_type_field(text: str, new_type: str) -> str:
    """Replace the ``type:`` line inside frontmatter, preserving everything else."""
    lines = text.split("\n")
    if lines and lines[0] == "---":
        for i in range(1, len(lines)):
            if lines[i].startswith("---"):
                break
            if lines[i].startswith("type:"):
                lines[i] = f"type: {new_type}"
                return "\n".join(lines)
        # type not present before closing fence → insert right after opening
        lines.insert(1, f"type: {new_type}")
        return "\n".join(lines)
    return text


def classify_wiki(
    wiki_dir: Path,
    cfg: ClassifyConfig,
    *,
    strategy_name: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Classify every (non-reserved) wiki page and optionally write it back.

    Returns a report with the per-type distribution. When not ``dry_run``, each
    page's ``type`` field is updated in place (idempotent) and ``index.md`` is
    rebuilt via :func:`build_index` so the hub stays consistent.
    """
    wiki_dir = Path(wiki_dir)
    strategy_name = strategy_name or cfg.strategy or "local"
    strategy = get_strategy(strategy_name, cfg)

    distribution: dict[str, int] = {}
    pages: list[tuple[Path, str]] = []  # (path, new_type)

    for md in sorted(wiki_dir.glob("*.md")):
        if md.name in _RESERVVED:
            continue
        text = md.read_text(encoding="utf-8")
        meta, body = parse(text)
        slug = md.stem
        title = str(meta.get("title", slug))
        tags = [str(t) for t in (meta.get("tags", []) or [])]
        new_type = strategy.classify(slug, title, tags, body)
        distribution[new_type] = distribution.get(new_type, 0) + 1
        if not dry_run:
            pages.append((md, _set_type_field(text, new_type)))

    if not dry_run:
        for md, new_text in pages:
            md.write_text(new_text, encoding="utf-8")
        # refresh the hub so index.md reflects the new types
        build_index(wiki_dir)

    return {
        "strategy": strategy_name,
        "dry_run": dry_run,
        "total": sum(distribution.values()),
        "distribution": distribution,
    }
