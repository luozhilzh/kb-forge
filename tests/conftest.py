"""Shared pytest fixtures: build the synthetic KB into a temp dir."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from kbforge.config import KbForgeConfig, PathsConfig
from kbforge.core import run

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "sample_kb"
RESERVED = {"index.md", "log.md"}


@pytest.fixture
def sample_kb(tmp_path: Path) -> Path:
    dest = tmp_path / "sample_kb"
    shutil.copytree(FIXTURE_DIR, dest)
    return dest


@pytest.fixture
def built_wiki(sample_kb: Path) -> Path:
    cfg = KbForgeConfig(root=sample_kb, paths=PathsConfig())
    run(cfg)
    return sample_kb / "wiki"
