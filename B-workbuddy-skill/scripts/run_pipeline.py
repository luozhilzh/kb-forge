#!/usr/bin/env python3
"""Thin wrapper that drives the kbforge CLI end-to-end.

This reproduces exactly how the B (WorkBuddy Skill) and the expert package call
core: via the `kbforge` CLI as a subprocess. It does NOT import kbforge internals.

Usage:
    python run_pipeline.py --kb-root <dir> [--format pptx] [--out <file>] [--dry-run]
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the kbforge pipeline (build + export).")
    ap.add_argument("--kb-root", required=True, type=Path, help="Knowledge-base root.")
    ap.add_argument("--format", default="pptx", choices=["md", "pptx", "html"])
    ap.add_argument("--out", default=None, type=Path, help="Export output path.")
    ap.add_argument("--dry-run", action="store_true", help="Build preview only; no export.")
    args = ap.parse_args()

    kb = str(args.kb_root.resolve())

    # 1) build
    build = [sys.executable, "-m", "kbforge", "build", "--kb-root", kb]
    if args.dry_run:
        build.append("--dry-run")
    subprocess.run(build, check=True)
    if args.dry_run:
        return 0

    # 2) export
    export = [
        sys.executable, "-m", "kbforge", "export",
        "--kb-root", kb, "--format", args.format,
    ]
    if args.out:
        export += ["--out", str(args.out)]
    subprocess.run(export, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
