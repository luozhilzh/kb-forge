"""MCP server for kb-forge (the agent-native delivery form).

Exposes the local-first core toolkit as a set of standard MCP tools so any LLM
agent can *forge* and *query* a knowledge base without leaving its loop. This is
the product closure of the RAG pipeline: ``query`` / ``export`` / ``site`` /
``enrich`` / ``diff`` / ``validate`` / ``build``, all callable over MCP.

Design notes:
  * The ``mcp`` dependency is **optional** and imported lazily inside
    :func:`create_server`. Importing this module (or its tool functions) never
    requires ``mcp`` to be installed — only *running* the server does. This keeps
    the base ``kbforge`` install lean and the tool functions directly testable.
  * Every tool returns serializable data (``list[dict]`` / ``dict`` / ``str``),
    matching the MCP-friendly contract already established for ``query``/``diff``.
  * No external model or vector store is touched — the server wraps the same
    zero-dependency local tools as the CLI / B skill / expert package.

Run it (after ``pip install 'kbforge[mcp]'``) with ``kbforge mcp`` (stdio, the
default for local agents) or ``python -m kbforge mcp --transport sse``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import load_config
from .core import run
from .core.diff import diff_wiki, validate_wiki
from .core.enrich import enrich_wiki, get_strategy
from .core.exporters import extract_bundles, get_exporter
from .core.query import query_wiki
from .core.site import build_site, SUPPORTED_THEMES


# --------------------------------------------------------------------------- #
# Resolution helpers (shared shape with the CLI)
# --------------------------------------------------------------------------- #
def _resolve_wiki(kb_root: str | None, wiki_dir: str | None) -> Path:
    """Resolve the compiled wiki dir from an explicit path or a kb root."""
    if wiki_dir:
        return Path(wiki_dir)
    start = Path(kb_root) if kb_root else Path.cwd()
    cfg = load_config(start_dir=start)
    return cfg.path("wiki")


def _export_out_path(
    kb_root: str | None, wiki_dir: str | None, out: str | None, suffix: str
) -> Path:
    if out:
        return Path(out)
    if wiki_dir:
        return Path(wiki_dir).parent / f"export{suffix}"
    start = Path(kb_root) if kb_root else Path.cwd()
    return start / f"export{suffix}"


def _site_out_dir(
    kb_root: str | None, wiki_dir: str | None, out: str | None
) -> Path:
    if out:
        return Path(out)
    if wiki_dir:
        return Path(wiki_dir).parent / "site_src"
    start = Path(kb_root) if kb_root else Path.cwd()
    return start / "site_src"


# --------------------------------------------------------------------------- #
# Tool functions (pure logic; no mcp import here, so they are directly testable)
# --------------------------------------------------------------------------- #
def tool_query(
    text: str,
    kb_root: str | None = None,
    wiki_dir: str | None = None,
    top_k: int = 5,
    backend: str = "graph",
) -> list[dict[str, Any]]:
    """Retrieve relevant wiki pages for a query (RAG-ready).

    Args:
        text: natural-language query.
        kb_root: knowledge-base root (config-derived wiki is used if wiki_dir is
            not given).
        wiki_dir: compiled wiki dir; takes precedence over kb_root.
        top_k: maximum number of hits to return.
        backend: ``graph`` (Personalized PageRank, zero-dep, default) or
            ``embedding`` (optional extension point, OFF by default).

    Returns:
        A list of hit dicts: ``{id, score, snippet, source_path, link}``.
    """
    wiki = _resolve_wiki(kb_root, wiki_dir)
    results = query_wiki(wiki, text, top_k=top_k, backend=backend)
    return [r.to_dict() for r in results]


def tool_export(
    kb_root: str | None = None,
    wiki_dir: str | None = None,
    format: str = "pptx",
    out: str | None = None,
    types: str = "case,pitfall,concept",
) -> str:
    """Extract case/pitfall bundles from a built wiki and render to a file.

    Args:
        kb_root / wiki_dir: see :func:`tool_query`.
        format: ``pptx`` | ``html`` | ``md``.
        out: output path (extension auto-corrected); defaults next to the wiki.
        types: comma list of wiki page types to include.

    Returns:
        The absolute path of the written export file.
    """
    wiki = _resolve_wiki(kb_root, wiki_dir)
    wanted = {t.strip() for t in types.split(",") if t.strip()}
    bundles = extract_bundles(wiki, types=frozenset(wanted))
    if not bundles:
        raise ValueError(
            f"No wiki pages of types {sorted(wanted)} found in {wiki}"
        )
    exporter = get_exporter(format)
    out_path = _export_out_path(kb_root, wiki_dir, out, exporter.suffix)
    written = exporter.export(bundles, out_path)
    return str(written)


def tool_build_site(
    kb_root: str | None = None,
    wiki_dir: str | None = None,
    out: str | None = None,
    site_name: str = "KB Forge Wiki",
    theme: str = "material",
    build: bool = False,
) -> str:
    """Generate a browsable, searchable MkDocs site from a built wiki.

    Args:
        kb_root / wiki_dir: see :func:`tool_query`.
        out: output MkDocs project dir; defaults to ``<root>/site_src``.
        site_name: site title.
        theme: ``material`` | ``readthedocs`` | ``mkdocs``.
        build: if True, also run ``mkdocs build`` when mkdocs is available.

    Returns:
        The absolute path of the generated MkDocs project directory.
    """
    if theme not in SUPPORTED_THEMES:
        raise ValueError(
            f"Unsupported theme {theme!r}; choose from {sorted(SUPPORTED_THEMES)}"
        )
    wiki = _resolve_wiki(kb_root, wiki_dir)
    out_dir = _site_out_dir(kb_root, wiki_dir, out)
    build_site(wiki, out_dir, site_name=site_name, theme=theme, build=build)
    return str(out_dir)


def tool_enrich(
    kb_root: str | None = None,
    wiki_dir: str | None = None,
    strategy: str = "local",
) -> dict[str, list[dict[str, Any]]]:
    """Extract claim-level source anchors from a built wiki (RAG citing).

    Args:
        kb_root / wiki_dir: see :func:`tool_query`.
        strategy: ``local`` (zero-dep sentence/claim splitter) or ``none``
            (no-op baseline).

    Returns:
        A mapping ``slug -> [claim dict]`` where each claim carries a
        ``source_anchor`` pointing back to its origin post.
    """
    wiki = _resolve_wiki(kb_root, wiki_dir)
    return enrich_wiki(wiki, strategy=get_strategy(strategy))


def tool_validate(
    kb_root: str | None = None,
    wiki_dir: str | None = None,
) -> list[dict[str, Any]]:
    """Check a built wiki against the OKF contract.

    Args:
        kb_root / wiki_dir: see :func:`tool_query`.

    Returns:
        A list of violation dicts (empty when the wiki is compliant).
    """
    wiki = _resolve_wiki(kb_root, wiki_dir)
    return [v.to_dict() for v in validate_wiki(wiki)]


def tool_diff(
    kb_root: str | None = None,
    wiki_dir: str | None = None,
    before: str | None = None,
) -> dict[str, Any]:
    """Detect knowledge-base drift after a re-ingest (OKF anti-drift guard).

    Args:
        kb_root / wiki_dir: see :func:`tool_query`.
        before: compare against this wiki dir instead of the saved baseline
            snapshot (``<wiki>/.wiki_snapshot.json``).

    Returns:
        A diff-report dict: added / removed / changed / broken_links /
        orphan_refs / contract_violations, plus ``baseline_created`` on first run.
    """
    wiki = _resolve_wiki(kb_root, wiki_dir)
    before_dir = Path(before) if before else None
    return diff_wiki(wiki, before_dir=before_dir).to_dict()


def tool_build(
    kb_root: str,
    stage: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Compile the OKF wiki from a knowledge-base root (archive -> wiki).

    Args:
        kb_root: knowledge-base root (must contain a ``config.yaml`` / archive).
        stage: ``None``/``wiki`` (ingest + index) | ``ingest`` | ``index``.
        dry_run: compute but do not write files.

    Returns:
        A run-report dict: ingested / wiki_writes / schema_warnings / dry_run.
    """
    cfg = load_config(start_dir=Path(kb_root))
    return run(cfg, stage=stage, dry_run=dry_run)


# --------------------------------------------------------------------------- #
# Server factory (lazy mcp import)
# --------------------------------------------------------------------------- #
def create_server(name: str = "kb-forge"):
    """Build and return the FastMCP server with all kb-forge tools registered.

    Raises ``ImportError`` (with a helpful hint) if the ``mcp`` package is not
    installed — callers should translate that into a friendly message.
    """
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:  # pragma: no cover - depends on optional dep
        raise ImportError(
            "The kb-forge MCP server requires the 'mcp' package. "
            "Install with: pip install 'kbforge[mcp]'"
        ) from exc

    mcp = FastMCP(name)
    mcp.tool(name="query")(tool_query)
    mcp.tool(name="export")(tool_export)
    mcp.tool(name="build_site")(tool_build_site)
    mcp.tool(name="enrich")(tool_enrich)
    mcp.tool(name="validate")(tool_validate)
    mcp.tool(name="diff")(tool_diff)
    mcp.tool(name="build")(tool_build)
    return mcp


def run_server(transport: str = "stdio") -> None:
    """Run the kb-forge MCP server (blocks; stdio by default for local agents)."""
    server = create_server()
    server.run(transport=transport)
