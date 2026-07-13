"""Generate a browsable, searchable static site (MkDocs) from a compiled wiki.

The compiled wiki (see :mod:`kbforge.core.wiki`) is a flat directory of
``<slug>.md`` pages, each with YAML frontmatter (``type`` / ``title`` / ...) and
``[[wiki-link]]`` syntax in the body.

This module turns that into a **self-contained MkDocs project**:

* ``[[slug]]`` / ``[[slug|label]]`` is rewritten to a real ``[label](slug.md)``
  link at *generate* time, so the generated site builds with **stock MkDocs** —
  no custom build hook, no extra dependency.
* ``mkdocs.yml`` is emitted with a type-grouped ``nav`` and the built-in search
  plugin, so the result is immediately searchable.
* ``build=True`` optionally runs ``mkdocs build`` if ``mkdocs`` is on ``PATH``
  (skipped silently otherwise — ``kbforge`` itself never requires MkDocs).

The output is plain MkDocs, so any theme the user has installed works.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import yaml

from .frontmatter import dump, parse

_LINK_RE = re.compile(r"\[\[([^\]\|]+)(?:\|([^\]]+))?\]\]")
_RESERVED = {"index.md", "log.md"}
SUPPORTED_THEMES = frozenset({"material", "readthedocs", "mkdocs"})


def _slug_target(slug: str) -> str:
    """Relative link target for a page, assuming a flat ``docs/`` layout."""
    return f"{slug}.md"


def _rewrite_links(body: str, titles: dict[str, str]) -> str:
    def repl(m: re.Match) -> str:
        slug = m.group(1).strip()
        label = (m.group(2) or "").strip() or titles.get(slug, slug)
        if slug in titles:
            return f"[{label}]({_slug_target(slug)})"
        # Unknown slug: keep the literal so we never emit a broken link.
        return m.group(0)

    return _LINK_RE.sub(repl, body)


def _render_mkdocs_yml(site_name: str, nav: list, theme: str) -> str:
    cfg = {
        "site_name": site_name,
        "docs_dir": "docs",
        "theme": {
            "name": theme,
            "features": [
                "navigation.sections",
                "navigation.top",
                "content.code.copy",
                "search.suggest",
                "search.highlight",
            ],
        },
        "plugins": ["search"],
        "nav": nav,
    }
    return yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False).strip() + "\n"


def build_site(
    wiki_dir: Path,
    out_dir: Path,
    *,
    site_name: str = "KB Forge Wiki",
    theme: str = "material",
    build: bool = False,
) -> list[Path]:
    """Turn a compiled ``wiki_dir`` into a MkDocs project under ``out_dir``.

    Returns the list of written paths (the generated ``docs/`` pages, the landing
    ``index.md``, and ``mkdocs.yml``; plus the built ``site/`` if ``build=True``
    and ``mkdocs`` is available).
    """
    if theme not in SUPPORTED_THEMES:
        raise ValueError(f"Unsupported theme {theme!r}; choose from {sorted(SUPPORTED_THEMES)}")

    wiki_dir = Path(wiki_dir)
    out_dir = Path(out_dir)
    docs = out_dir / "docs"
    docs.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []

    # 1) collect pages
    pages: list[dict] = []
    for md in sorted(wiki_dir.glob("*.md")):
        if md.name in _RESERVED or md.name.startswith("."):
            continue
        meta, body = parse(md.read_text(encoding="utf-8"))
        slug = md.stem
        pages.append(
            {
                "slug": slug,
                "type": str(meta.get("type", "post")),
                "title": str(meta.get("title", slug)),
                "meta": meta,
                "body": body,
            }
        )

    # 2) slug -> title map (so [[links]] resolve to a friendly label)
    titles = {p["slug"]: p["title"] for p in pages}

    # 3) write each page with links resolved
    for p in pages:
        body = _rewrite_links(p["body"], titles)
        out = docs / f"{p['slug']}.md"
        out.write_text(dump(p["meta"], body), encoding="utf-8")
        written.append(out)

    # 4) landing index.md, grouped by type
    by_type: dict[str, list[dict]] = {}
    for p in pages:
        by_type.setdefault(p["type"], []).append(p)

    index_lines = ["---", "type: index", f"title: {site_name}", "---", "", f"# {site_name}", ""]
    for t in sorted(by_type):
        index_lines.append(f"## {t.capitalize()}")
        for p in by_type[t]:
            index_lines.append(f"- [{p['title']}]({_slug_target(p['slug'])})")
        index_lines.append("")
    index_path = docs / "index.md"
    index_path.write_text("\n".join(index_lines), encoding="utf-8")
    written.append(index_path)

    # 5) mkdocs.yml with a type-grouped nav
    nav = [{"Home": "index.md"}]
    for t in sorted(by_type):
        nav.append({t.capitalize(): [_slug_target(p["slug"]) for p in by_type[t]]})
    yml_path = out_dir / "mkdocs.yml"
    yml_path.write_text(_render_mkdocs_yml(site_name, nav, theme), encoding="utf-8")
    written.append(yml_path)

    # 6) optional build (only if mkdocs is installed)
    if build:
        _try_build(out_dir, written)

    return written


def _try_build(out_dir: Path, written: list[Path]) -> None:
    import sys

    # Prefer a `mkdocs` on PATH; fall back to the interpreter running kbforge
    # (in case mkdocs lives in the same environment). Building is best-effort.
    mkdocs = shutil.which("mkdocs")
    if mkdocs:
        cmd: list[str] = [mkdocs, "build", "-d", "site"]
    else:
        cmd = [sys.executable, "-m", "mkdocs", "build", "-d", "site"]

    try:
        subprocess.run(cmd, cwd=str(out_dir), check=True, capture_output=True, text=True)
        built = out_dir / "site"
        if built.exists():
            written.append(built)
    except (subprocess.CalledProcessError, OSError):
        # Building is best-effort; the generated project is still valid.
        pass
