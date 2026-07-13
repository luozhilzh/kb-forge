"""Golden tests for the MkDocs site generator (build_site).

Verifies that a compiled wiki becomes a self-contained, stock-MkDocs-buildable
project: every page copied with ``[[wiki-link]]`` resolved, a type-grouped nav,
and a valid ``mkdocs.yml``. Building is never exercised here (mkdocs is not a
kb-forge dependency); ``build=False`` keeps the test hermetic.
"""

from __future__ import annotations

import yaml
from pathlib import Path

from kbforge.core.site import build_site, SUPPORTED_THEMES


def test_build_site_emits_project(built_wiki, tmp_path) -> None:
    out = tmp_path / "site_src"
    written = build_site(built_wiki, out, site_name="Demo", theme="material", build=False)

    # mkdocs.yml + docs/index.md + one doc per wiki page
    assert (out / "mkdocs.yml").exists()
    assert (out / "docs" / "index.md").exists()
    for slug in ("t101-rag-eval", "t102-chunk-strategy", "t103-gpu-cost"):
        assert (out / "docs" / f"{slug}.md").exists()
    assert len(written) >= 5


def test_wiki_links_resolved_to_markdown(built_wiki, tmp_path) -> None:
    out = tmp_path / "site_src"
    build_site(built_wiki, out, build=False)

    t101 = (out / "docs" / "t101-rag-eval.md").read_text(encoding="utf-8")
    # [[t102-chunk-strategy]] -> [分块策略对召回的影响](t102-chunk-strategy.md)
    assert "[分块策略对召回的影响](t102-chunk-strategy.md)" in t101
    assert "[推理成本被忽视的坑](t103-gpu-cost.md)" in t101
    # raw [[...]] syntax must be gone
    assert "[[" not in t101


def test_unknown_slug_kept_literal(built_wiki, tmp_path) -> None:
    from kbforge.core.site import _rewrite_links

    # unknown slugs (with or without label) stay literal -> never a broken link
    resolved = _rewrite_links("见 [[nonexistent-slug]] 与 [[ghost|幽灵]]。", {"known": "K"})
    assert "[[nonexistent-slug]]" in resolved
    assert "[[ghost|幽灵]]" in resolved
    # known slug still resolves, label honored
    assert "[Y](known.md)" in _rewrite_links("[[known|Y]]", {"known": "K"})


def test_mkdocs_yml_is_valid_and_grouped(built_wiki, tmp_path) -> None:
    out = tmp_path / "site_src"
    build_site(built_wiki, out, site_name="Demo", theme="material", build=False)

    cfg = yaml.safe_load((out / "mkdocs.yml").read_text(encoding="utf-8"))
    assert cfg["site_name"] == "Demo"
    assert cfg["docs_dir"] == "docs"
    assert cfg["theme"]["name"] == "material"
    assert "search" in cfg["plugins"]
    # nav: Home + one section per type, every page referenced exactly once
    flat: list[str] = []
    for entry in cfg["nav"]:
        for value in entry.values():
            if isinstance(value, str):
                flat.append(value)
            else:
                flat.extend(value)
    assert "index.md" in flat
    for slug in ("t101-rag-eval", "t102-chunk-strategy", "t103-gpu-cost"):
        assert f"{slug}.md" in flat
    # no page missing, no duplicate
    assert len(flat) == len(set(flat))


def test_landing_index_lists_pages(built_wiki, tmp_path) -> None:
    out = tmp_path / "site_src"
    build_site(built_wiki, out, site_name="Demo", build=False)
    index = (out / "docs" / "index.md").read_text(encoding="utf-8")
    assert "# Demo" in index
    assert "[RAG 评测为什么不能只看准确率](t101-rag-eval.md)" in index
    assert "## Case" in index  # type-grouped heading
    assert "## Concept" in index
    assert "## Pitfall" in index


def test_unsupported_theme_rejected(built_wiki, tmp_path) -> None:
    import pytest

    with pytest.raises(ValueError):
        build_site(built_wiki, tmp_path / "x", theme="not-a-theme", build=False)
