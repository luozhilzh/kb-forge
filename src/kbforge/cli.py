"""kb-forge command-line interface (the "A" thin shell over core)."""

from __future__ import annotations

from pathlib import Path

import click

from .config import load_config
from .core import run
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


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
