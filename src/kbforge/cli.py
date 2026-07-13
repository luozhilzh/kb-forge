"""kb-forge command-line interface (the "A" thin shell over core)."""

from __future__ import annotations

from pathlib import Path

import click

from .config import load_config
from .core import run
from .core.exporters import get_exporter, extract_bundles
from .core.query import query_wiki
from .core.site import build_site, SUPPORTED_THEMES
from .core.diff import validate_wiki, diff_wiki
from .core.enrich import enrich_wiki, get_strategy
from .tools import make_fixtures


@click.group()
def cli() -> None:
    """kb-forge: forge community posts into an OKF-compatible knowledge base."""


@cli.command("make-fixtures")
@click.option(
    "--out",
    default=Path("tests/fixtures/sample_kb"),
    type=click.Path(path_type=Path),
    help="Where to write the synthetic knowledge base.",
)
def make_fixtures_cmd(out: Path) -> None:
    """Generate a synthetic demo knowledge base (no real data)."""
    make_fixtures.generate(out)
    click.echo(f"Wrote synthetic knowledge base to {out}")


@cli.command("build")
@click.option("--kb-root", default=None, type=click.Path(path_type=Path), help="Knowledge-base root.")
@click.option("--profile", default=None, help="Config profile (config.<profile>.yaml).")
@click.option("--stage", default=None, help="wiki | ingest | index.")
@click.option("--topic", default=None, help="Restrict to a single topic id (filename stem).")
@click.option("--dry-run", is_flag=True, help="Compute but do not write files.")
def build_cmd(kb_root, profile, stage, topic, dry_run) -> None:
    """Compile the wiki from a knowledge root."""
    cfg = load_config(profile=profile, start_dir=Path.cwd())
    if kb_root:
        cfg.root = Path(kb_root).resolve()
    report = run(cfg, stage=stage, topic=topic, dry_run=dry_run)
    click.echo(report)


@cli.command("export")
@click.option("--kb-root", default=None, type=click.Path(path_type=Path), help="Knowledge-base root.")
@click.option("--wiki-dir", default=None, type=click.Path(path_type=Path), help="Use an already-built wiki dir instead of <kb-root>/wiki.")
@click.option("--format", "fmt", default="pptx", type=click.Choice(["md", "pptx", "html"]), help="Output format.")
@click.option("--out", default=None, type=click.Path(path_type=Path), help="Output path (extension auto-corrected).")
@click.option("--types", default="case,pitfall,concept", help="Comma list of wiki page types to include.")
def export_cmd(kb_root, wiki_dir, fmt, out, types):
    """Extract case bundles from a built wiki and render them to a format."""
    cfg = load_config(start_dir=Path.cwd())
    if kb_root:
        cfg.root = Path(kb_root).resolve()
    wiki = Path(wiki_dir) if wiki_dir else cfg.path("wiki")
    wanted = {t.strip() for t in types.split(",") if t.strip()}
    bundles = extract_bundles(wiki, types=frozenset(wanted))
    if not bundles:
        raise click.ClickException(f"No wiki pages of types {sorted(wanted)} found in {wiki}")
    exporter = get_exporter(fmt)
    out_path = Path(out) if out else (cfg.root / f"export{exporter.suffix}")
    written = exporter.export(bundles, out_path)
    click.echo(f"Exported {len(bundles)} bundles -> {written}")


@cli.command("query")
@click.argument("query_text")
@click.option("--kb-root", default=None, type=click.Path(path_type=Path), help="Knowledge-base root.")
@click.option("--wiki-dir", default=None, type=click.Path(path_type=Path), help="Use an already-built wiki dir instead of <kb-root>/wiki.")
@click.option("--top-k", default=5, type=int, help="Max number of hits.")
@click.option("--backend", default=None, type=click.Choice(["graph", "embedding"]), help="Retriever backend (default: from config).")
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json"]), help="text=human readable, json=serializable (MCP-friendly).")
def query_cmd(query_text, kb_root, wiki_dir, top_k, backend, fmt):
    """Retrieve relevant wiki pages for a query (RAG-ready)."""
    import json

    cfg = load_config(start_dir=Path.cwd())
    if kb_root:
        cfg.root = Path(kb_root).resolve()
    wiki = Path(wiki_dir) if wiki_dir else cfg.path("wiki")
    backend = backend or cfg.query.backend
    results = query_wiki(wiki, query_text, top_k=top_k, backend=backend)
    if fmt == "json":
        click.echo(json.dumps([r.to_dict() for r in results], ensure_ascii=False, indent=2))
    else:
        if not results:
            click.echo("(no hits)")
        for r in results:
            click.echo(f"{r.score:.4f}  [{r.id}]  {r.snippet}")


@cli.command("site")
@click.option("--kb-root", default=None, type=click.Path(path_type=Path), help="Knowledge-base root.")
@click.option("--wiki-dir", default=None, type=click.Path(path_type=Path), help="Use an already-built wiki dir instead of <kb-root>/wiki.")
@click.option("--out", default=None, type=click.Path(path_type=Path), help="Output MkDocs project dir (default: <kb-root>/site_src).")
@click.option("--site-name", default="KB Forge Wiki", help="Site title.")
@click.option("--theme", default="material", type=click.Choice(sorted(SUPPORTED_THEMES)), help="MkDocs theme (mkdocs-material required for 'material').")
@click.option("--build/--no-build", default=True, help="Run `mkdocs build` if mkdocs is on PATH.")
def site_cmd(kb_root, wiki_dir, out, site_name, theme, build):
    """Generate a browsable, searchable MkDocs site from a built wiki."""
    cfg = load_config(start_dir=Path.cwd())
    if kb_root:
        cfg.root = Path(kb_root).resolve()
    wiki = Path(wiki_dir) if wiki_dir else cfg.path("wiki")
    out_dir = Path(out) if out else (cfg.root / "site_src")
    written = build_site(wiki, out_dir, site_name=site_name, theme=theme, build=build)
    click.echo(f"Generated MkDocs site project -> {out_dir}")
    click.echo(f"  Next: cd {out_dir} && mkdocs serve")


@cli.command("validate")
@click.option("--kb-root", default=None, type=click.Path(path_type=Path), help="Knowledge-base root.")
@click.option("--wiki-dir", default=None, type=click.Path(path_type=Path), help="Use an already-built wiki dir instead of <kb-root>/wiki.")
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json"]), help="text=human readable, json=serializable (MCP-friendly).")
def validate_cmd(kb_root, wiki_dir, fmt):
    """Check a built wiki against the OKF contract (type/hash/broken links)."""
    import json

    cfg = load_config(start_dir=Path.cwd())
    if kb_root:
        cfg.root = Path(kb_root).resolve()
    wiki = Path(wiki_dir) if wiki_dir else cfg.path("wiki")
    violations = validate_wiki(wiki)
    if fmt == "json":
        click.echo(json.dumps([v.to_dict() for v in violations], ensure_ascii=False, indent=2))
    else:
        if not violations:
            n_pages = len([p for p in wiki.glob("*.md") if p.name not in {"index.md", "log.md"}])
            click.echo(f"OK: {wiki} is OKF-compliant ({n_pages} pages checked)")
            return
        for v in violations:
            click.echo(f"[{v.kind}] {v.slug}: {v.detail}")
        raise click.ClickException(f"{len(violations)} OKF violation(s) found — see above")


@cli.command("diff")
@click.option("--kb-root", default=None, type=click.Path(path_type=Path), help="Knowledge-base root.")
@click.option("--wiki-dir", default=None, type=click.Path(path_type=Path), help="Use an already-built wiki dir instead of <kb-root>/wiki.")
@click.option("--before", default=None, type=click.Path(path_type=Path), help="Compare against this wiki dir instead of the saved baseline snapshot.")
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json"]), help="text=human readable, json=serializable (MCP-friendly).")
def diff_cmd(kb_root, wiki_dir, before, fmt):
    """Detect knowledge-base drift after a re-ingest (OKF anti-drift guard)."""
    import json

    cfg = load_config(start_dir=Path.cwd())
    if kb_root:
        cfg.root = Path(kb_root).resolve()
    wiki = Path(wiki_dir) if wiki_dir else cfg.path("wiki")
    report = diff_wiki(wiki, before_dir=before)
    if fmt == "json":
        click.echo(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
        return
    if report.baseline_created:
        click.echo(f"Baseline snapshot created at {wiki / '.wiki_snapshot.json'}.")
        click.echo("Re-run after a re-ingest to see drift.")
        return
    lines: list[str] = []
    if report.added:
        lines.append(f"Added ({len(report.added)}): {', '.join(report.added)}")
    if report.removed:
        lines.append(f"Removed ({len(report.removed)}): {', '.join(report.removed)}")
    if report.changed:
        lines.append("Changed:")
        for s, ds in report.changed.items():
            for d in ds:
                lines.append(f"  - {s}: {d}")
    if report.broken_links:
        lines.append("Broken links:")
        for s, ts in report.broken_links.items():
            lines.append("  - " + s + ": " + ", ".join(f"[[{t}]]" for t in ts))
    if report.orphan_refs:
        lines.append(f"Orphan refs ({len(report.orphan_refs)}): {', '.join(report.orphan_refs)}")
    if report.contract_violations:
        lines.append(f"Contract violations ({len(report.contract_violations)}):")
        for v in report.contract_violations:
            lines.append(f"  - [{v.kind}] {v.slug}: {v.detail}")
    if not lines:
        lines.append("No drift detected.")
    click.echo("\n".join(lines))


@cli.command("enrich")
@click.option("--kb-root", default=None, type=click.Path(path_type=Path), help="Knowledge-base root.")
@click.option("--wiki-dir", default=None, type=click.Path(path_type=Path), help="Use an already-built wiki dir instead of <kb-root>/wiki.")
@click.option("--strategy", default="local", type=click.Choice(["local", "none"]), help="Claim extraction strategy ('none' = no-op).")
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json"]), help="text=human readable, json=serializable (MCP-friendly).")
def enrich_cmd(kb_root, wiki_dir, strategy, fmt):
    """Extract claim-level source anchors from a built wiki (RAG citing)."""
    import json

    cfg = load_config(start_dir=Path.cwd())
    if kb_root:
        cfg.root = Path(kb_root).resolve()
    wiki = Path(wiki_dir) if wiki_dir else cfg.path("wiki")
    result = enrich_wiki(wiki, strategy=get_strategy(strategy))
    if fmt == "json":
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
        return
    total = sum(len(v) for v in result.values())
    if not total:
        click.echo("(no claims extracted)")
        return
    for slug, claims in result.items():
        click.echo(f"## {slug} ({len(claims)} claims)")
        for c in claims:
            click.echo(f"  - [{c['source_anchor']}] {c['text']}")


@cli.command("mcp")
@click.option(
    "--transport",
    default="stdio",
    type=click.Choice(["stdio", "sse"]),
    help="MCP transport. stdio is the default for local agents; sse for remote.",
)
def mcp_cmd(transport):
    """Run the kb-forge MCP server (exposes query/export/site/enrich/validate/diff/build)."""
    from .mcp_server import run_server

    try:
        run_server(transport=transport)
    except ImportError as exc:
        raise click.ClickException(str(exc))


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
