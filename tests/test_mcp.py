"""kb-forge MCP server tests.

Two layers:

1. Tool-function tests (always run, no ``mcp`` dependency). The tool functions in
   ``kbforge.mcp_server`` contain the real logic and are directly callable, so we
   exercise them against a built wiki without spinning up a server.
2. Registration guard (runs only when ``mcp`` is installed). Verifies
   :func:`create_server` wires up exactly the expected tool set. Skipped on
   environments without the optional ``mcp`` extra.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from kbforge.mcp_server import (
    tool_build,
    tool_build_site,
    tool_diff,
    tool_enrich,
    tool_export,
    tool_query,
    tool_validate,
)

ALL_TOOL_NAMES = {"query", "export", "build_site", "enrich", "validate", "diff", "build"}


# --------------------------------------------------------------------------- #
# Tool-function tests (no mcp needed)
# --------------------------------------------------------------------------- #
def test_query_tool_returns_serializable(built_wiki: Path) -> None:
    hits = tool_query("RAG 评测", wiki_dir=str(built_wiki), top_k=3)
    assert isinstance(hits, list) and hits
    for h in hits:
        assert set(h) >= {"id", "score", "snippet"}
        assert isinstance(h["score"], float)


def test_validate_tool_clean_wiki_has_no_violations(built_wiki: Path) -> None:
    violations = tool_validate(wiki_dir=str(built_wiki))
    assert violations == []


def test_enrich_tool_local_returns_anchored_claims(built_wiki: Path) -> None:
    claims = tool_enrich(wiki_dir=str(built_wiki), strategy="local")
    assert isinstance(claims, dict) and claims
    for slug, clist in claims.items():
        assert isinstance(slug, str)
        for c in clist:
            assert set(c) >= {"text", "source_anchor", "slug"}


def test_diff_tool_baseline_then_changed(built_wiki: Path, tmp_path: Path) -> None:
    # First run creates a baseline.
    first = tool_diff(wiki_dir=str(built_wiki))
    assert first["baseline_created"] is True

    # Copy the wiki and edit one page (change content_hash) + add a page.
    other = tmp_path / "wiki2"
    import shutil

    shutil.copytree(built_wiki, other)
    target = other / "t101-rag-eval.md"
    text = target.read_text(encoding="utf-8")
    text = text.replace("content_hash:", "content_hash: sha256:deadbeef", 1)
    target.write_text(text + "\n新增一句：指标约 0.9。\n", encoding="utf-8")
    (other / "t999-new.md").write_text(
        "---\ntype: concept\ntitle: New\ncontent_hash: sha256:new\n---\n新页面。\n",
        encoding="utf-8",
    )

    report = tool_diff(wiki_dir=str(other), before=str(built_wiki))
    assert report["baseline_created"] is False
    assert "t999-new" in report["added"]
    assert "t101-rag-eval" in report["changed"]


def test_export_tool_writes_file(built_wiki: Path, tmp_path: Path) -> None:
    out = tmp_path / "cases.md"
    written = tool_export(
        wiki_dir=str(built_wiki), format="md", out=str(out), types="case"
    )
    assert Path(written).exists()
    assert Path(written).read_text(encoding="utf-8").strip()  # non-empty


def test_build_site_tool_writes_project(built_wiki: Path, tmp_path: Path) -> None:
    out = tmp_path / "site_src"
    project = tool_build_site(
        wiki_dir=str(built_wiki), out=str(out), theme="mkdocs", build=False
    )
    assert Path(project).exists()
    assert (Path(project) / "mkdocs.yml").exists()
    assert (Path(project) / "docs").is_dir()


def test_build_tool_runs_on_generated_kb(tmp_path: Path) -> None:
    # Construct a minimal, real KB root (config + archive + SCHEMA) so the
    # build tool exercises the actual ingest -> index pipeline.
    kb = tmp_path / "kb"
    kb.mkdir()
    (kb / "config.default.yaml").write_text('kb_root: "."\n', encoding="utf-8")
    (kb / "SCHEMA.md").write_text("# Topics\n", encoding="utf-8")
    arch = kb / "archive" / "2026" / "07"
    arch.mkdir(parents=True)
    (arch / "t900-demo.md").write_text(
        "---\ntopic_id: \"900\"\ntype: case\ntitle: Demo\n---\n正文内容。\n",
        encoding="utf-8",
    )
    # dry_run still ingests (computes pages) without writing.
    report = tool_build(kb_root=str(kb), dry_run=True)
    assert report["dry_run"] is True
    assert report["ingested"] == 1
    # A real run writes the compiled wiki.
    tool_build(kb_root=str(kb))
    assert (kb / "wiki" / "t900-demo.md").exists()


# --------------------------------------------------------------------------- #
# Registration guard (only when mcp is installed)
# --------------------------------------------------------------------------- #
def test_create_server_registers_all_tools() -> None:
    mcp = pytest.importorskip("mcp")
    from kbforge.mcp_server import create_server

    server = create_server()
    # FastMCP exposes registered tools via its tool manager.
    registered = set(server._tool_manager._tools.keys())
    assert ALL_TOOL_NAMES <= registered
