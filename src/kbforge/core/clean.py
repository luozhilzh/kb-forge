"""Body-level cleaning for ingested posts (real-world data-noise reduction).

Targets the noise observed in paid-community exports (e.g. Zsxq): the
``## 摘要`` section is almost always a *truncated, redundant preview* of the
post body — it repeats the opening of ``## 正文`` and ends mid-sentence with an
ellipsis (``…`` / ``...``). Keeping it pollutes exports (PPT / HTML cards show
the truncated heading + clipped text) and duplicates content already present in
the body.

``clean_summary_section`` therefore:

* **removes** a ``## 摘要`` section when it is a clipping of the body (redundant
  truncated preview) — this is the bulk of the real noise (≈89% of posts);
* **strips** a trailing truncation marker from a *genuinely distinct* summary
  (kept, never silently deleted — we never drop unique content);
* **leaves** a distinct, complete summary untouched.

The cleaning is deterministic, dependency-free and idempotent, so it is safe to
run on every ingest and to re-run on an already-cleaned corpus.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field

# A summary heading: optional level 1-4, literal "摘要", optional trailing colon.
_SUMMARY_HEADING_RE = re.compile(r"^#{1,4}\s*摘要\s*[：:]?\s*$", re.MULTILINE)
# Any markdown heading line (used to find the end of a section / skip in summaries).
_HEADING_LINE_RE = re.compile(r"^#{1,6}\s+\S", re.MULTILINE)
# Trailing truncation marker: ellipsis char or 1-3 dots, optional surrounding space.
_TRUNCATION_RE = re.compile(r"[\u2026\.]{1,3}\s*$")

# Minimum normalized length before we trust a containment / fuzzy match, so that
# short common phrases are never mistaken for a body clipping.
_MIN_CLIP_LEN = 12
# Fuzzy ratio (difflib) above which a summary is treated as a body clipping.
_FUZZY_RATIO = 0.9


@dataclass
class CleanReport:
    """What ``clean_summary_section`` did to one body."""

    removed_summary: bool = False
    stripped_truncation: bool = False
    actions: list[str] = field(default_factory=list)


def _norm(text: str) -> str:
    """Whitespace-collapsed, stripped normalization for comparison."""
    return re.sub(r"\s+", "", text).strip()


def _section_bounds(text: str):
    """Return ``(heading_start, content_start, section_end)`` or ``None``.

    ``section_end`` is the start of the next heading (any level) or EOF.
    """
    m = _SUMMARY_HEADING_RE.search(text)
    if not m:
        return None
    heading_start = m.start()
    nl = text.find("\n", m.end())
    content_start = nl + 1 if nl != -1 else len(text)
    nxt = _HEADING_LINE_RE.search(text, content_start)
    section_end = nxt.start() if nxt else len(text)
    return heading_start, content_start, section_end


def _body_opening(rest: str, limit: int = 300) -> str:
    """Normalized first chunk of a body (used for fuzzy prefix matching)."""
    # Drop any leading heading/blank lines, take the first paragraph-ish slice.
    lines = rest.splitlines()
    buf: list[str] = []
    for ln in lines:
        if _HEADING_LINE_RE.match(ln):
            continue
        if not ln.strip():
            if buf:
                break
            continue
        buf.append(ln)
        if len("".join(buf)) >= limit:
            break
    return _norm(" ".join(buf))[:limit]


def _remove_section(body: str, heading_start: int, section_end: int) -> str:
    """Drop a ``## 摘要`` section, preserving a single blank line of separation.

    When the summary is the first thing in the body (the common case, right
    after frontmatter), the cleaned body starts directly at the next section so
    the serializer's own ``\\n\\n`` separator is not doubled.
    """
    prefix = body[:heading_start].rstrip("\n")
    if prefix.strip() == "":
        return body[section_end:].lstrip("\n")
    return prefix + "\n\n" + body[section_end:].lstrip("\n")


def clean_summary_section(body: str) -> tuple[str, CleanReport]:
    """Remove redundant truncated ``## 摘要`` previews; keep distinct ones.

    Returns ``(new_body, report)``. ``new_body == body`` when nothing changed.
    """
    report = CleanReport()
    bounds = _section_bounds(body)
    if bounds is None:
        return body, report
    heading_start, content_start, section_end = bounds
    summary_text = body[content_start:section_end].strip()

    # 1) Empty summary section -> just drop it.
    if not summary_text:
        report.removed_summary = True
        report.actions.append("removed empty ## 摘要 section")
        return _remove_section(body, heading_start, section_end), report

    norm = _TRUNCATION_RE.sub("", summary_text).strip()
    norm = _norm(norm)

    # The rest of the body (summary section removed) is what we compare against.
    rest = body[:heading_start] + body[section_end:]
    rest_norm = _norm(rest)
    opening = _body_opening(rest)

    is_clipping = False
    if norm:
        n = len(norm)
        # (a) The summary appears verbatim somewhere in the remaining body.
        if n >= _MIN_CLIP_LEN and norm in rest_norm:
            is_clipping = True
        # (b) The summary IS the opening of the body (heading-stripped). This is
        #     the typical Zsxq case — a short/long truncated preview of the
        #     first sentence. A 6+ char prefix is distinctive enough in Chinese.
        elif n >= 6 and opening and opening.startswith(norm):
            is_clipping = True
        # (c) Near-substring: the summary is a clipped preview that may differ by
        #     a typo (e.g. "GPT4" vs "GPT-4") or span into the 2nd sentence. We
        #     slide a same-length window over the normalized body and accept a
        #     high similarity. Bounded by post size, so cheap in practice.
        elif n >= _MIN_CLIP_LEN and len(rest_norm) >= n:
            step = max(1, n // 10)
            for i in range(0, len(rest_norm) - n + 1, step):
                if difflib.SequenceMatcher(
                    None, norm, rest_norm[i : i + n]
                ).ratio() >= _FUZZY_RATIO:
                    is_clipping = True
                    break

    if is_clipping:
        report.removed_summary = True
        report.actions.append("removed redundant ## 摘要 (truncated preview of body)")
        return _remove_section(body, heading_start, section_end), report

    # 2) Distinct summary: keep it, but strip a trailing truncation marker.
    if _TRUNCATION_RE.search(summary_text):
        new_summary = _TRUNCATION_RE.sub("", summary_text).rstrip()
        new_body = body[:content_start] + new_summary + body[section_end:]
        report.stripped_truncation = True
        report.actions.append("stripped trailing truncation marker from distinct ## 摘要")
        return new_body, report

    # 3) Distinct, complete summary -> keep as-is.
    report.actions.append("kept distinct ## 摘要 (no change)")
    return body, report


def clean_post_body(body: str) -> tuple[str, CleanReport]:
    """Run all body-level cleaners. Currently: summary dedup / truncation.

    This is the single entry point the ingest adapter calls, so future cleaners
    can be added here without touching the caller.
    """
    return clean_summary_section(body)


def split_frontmatter(text: str) -> tuple[str, str]:
    """Split a document into ``(frontmatter_block, body)``.

    The frontmatter block includes the surrounding ``---`` delimiters verbatim,
    so callers can reassemble the file without re-serializing YAML (which would
    reorder keys and churn diffs on real corpora). Returns ``("", text)`` when no
    valid frontmatter is present.
    """
    if not text.startswith("---"):
        return "", text
    # Find the closing delimiter on its own line.
    end = text.find("\n---", 3)
    if end == -1:
        return "", text
    after = text.find("\n", end + 4)
    if after == -1:
        after = len(text)
    fm = text[:after]
    body = text[after:].lstrip("\n")
    return fm, body
