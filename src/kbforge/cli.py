"""kb-forge command-line interface (the "A" thin shell over core)."""

from __future__ import annotations

from pathlib import Path

import click

from .config import load_config
from .core import run
from .core.exporters import get_exporter, extract_bundles
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


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
