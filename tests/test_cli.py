"""Regression tests for CLI behavior with self-contained wikis (no config).

A wiki produced by `ingest-archive` is self-contained (has `wiki/` + `SCHEMA.md`
but no `config.yaml`). Commands that receive `--wiki-dir` must run even when the
current directory has no project config file.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from kbforge.cli import cli
from kbforge.config import load_config


def _make_wiki(d: Path) -> Path:
    wiki = d / "wiki"
    wiki.mkdir(parents=True)
    (wiki / "index.md").write_text("# Wiki\n", encoding="utf-8")
    (wiki / "sample.md").write_text(
        "---\ntype: post\nid: sample\ncontent_hash: sha256:sampleplaceholder\n---\nbody text about RAG\n",
        encoding="utf-8",
    )
    return wiki


def test_load_config_require_false_no_file(tmp_path: Path) -> None:
    cfg = load_config(start_dir=tmp_path, require=False)
    assert cfg.root.resolve() == tmp_path.resolve()


def test_load_config_require_true_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_config(start_dir=tmp_path, require=True)


@pytest.mark.parametrize(
    "cmd_base",
    [
        ["validate"],
        ["query", "rag"],
        ["diff"],
        ["enrich"],
    ],
)
def test_commands_run_without_config(tmp_path: Path, monkeypatch, cmd_base) -> None:
    """Given --wiki-dir in a config-less cwd, commands must not FileNotFoundError."""
    wiki = _make_wiki(tmp_path)
    cmd = cmd_base + ["--wiki-dir", str(wiki)]
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(cli, cmd)
    assert result.exit_code == 0, result.output
