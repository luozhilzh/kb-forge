"""OKF v0.1 golden compliance test (§7.6).

Three hard rules from OKF:
  1. Every non-reserved .md has parseable YAML frontmatter.
  2. That frontmatter has a non-empty `type`.
  3. Reserved files (index.md / log.md) follow the convention.
Tolerates unknown types, missing optional fields, and broken links (no error).
"""

from __future__ import annotations

import json

import pytest

from kbforge.core.frontmatter import parse

RESERVED = {"index.md", "log.md"}


def assert_okf_compliant(wiki_dir: object) -> None:
    wiki_dir = __import__("pathlib").Path(wiki_dir)
    assert (wiki_dir / "index.md").exists(), "reserved index.md is missing"

    for md in wiki_dir.glob("*.md"):
        if md.name in RESERVED:
            continue
        text = md.read_text(encoding="utf-8")
        meta, _ = parse(text)
        assert isinstance(meta, dict), f"{md.name}: frontmatter is not a mapping"
        assert "type" in meta and str(meta.get("type", "")).strip(), (
            f"{md.name}: missing non-empty 'type' (OKF rule 2)"
        )

    graph = json.loads((wiki_dir / ".graph.json").read_text(encoding="utf-8"))
    assert graph["nodes"], "graph has no nodes"
    assert graph["edges"], "graph has no edges"


def test_wiki_output_is_okf_compliant(built_wiki) -> None:
    assert_okf_compliant(built_wiki)


def test_markdown_exporter_output_is_okf_compliant(sample_kb, tmp_path) -> None:
    from kbforge.config import KbForgeConfig, PathsConfig
    from kbforge.core import run
    from kbforge.core.exporters import get_exporter
    from kbforge.core.wiki.ingest import ingest_post

    cfg = KbForgeConfig(root=sample_kb, paths=PathsConfig())
    run(cfg)

    pages = [
        ingest_post(p)
        for p in sorted((sample_kb / "archive").glob("**/*.md"))
        if p.name not in RESERVED
    ]
    out = get_exporter("md").export(pages, tmp_path / "bundle.md")
    meta, _ = parse(out.read_text(encoding="utf-8"))
    assert meta.get("type") == "bundle"
