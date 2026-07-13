# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/) and this project adheres to
[Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-07-13

### Added
- Phase 0 skeleton: packaging, config contract, adapter abstraction.
- Synthetic fixture generator (`make-fixtures`) + hermetic `tests/fixtures/`.
- OKF v0.1 golden compliance test (`test_okf_compliance.py`).
- Thin slice: `config -> mock adapter -> ingest (content_hash) -> build_index`
  producing an OKF-compatible wiki.
- `MarkdownExporter` (minimal) demonstrating the pluggable output layer.
- CI: dual-matrix (Ubuntu + Windows) pytest, e2e on Ubuntu only.

### Added (Phase 2 exporters)
- `extract.py`: `CaseBundle` dataclass + `extract_bundles(wiki_dir)` reads built wiki
  pages (`type` filter, default `case/pitfall/concept`) and produces exporter-agnostic bundles.
- `PptxExporter`: built-in minimal template (no external .pptx dependency), generates a
  title slide + one slide per bundle via `python-pptx`.
- `HtmlExporter`: standalone self-contained HTML, one `<section>` per bundle (HTML-escaped).
- `export` CLI command: `kbforge export --format pptx|html|md [--types ...] [--out ...]`.
- Golden tests: `test_exporters.py` (extract shape + pptx/html round-trip + md).

### Added (Phase 2 delivery forms: B skill + expert)
- `B-workbuddy-skill/`: WorkBuddy Skill — `SKILL.md` (trigger words + drives core
  via `kbforge` CLI subprocess + compliance red lines), `references/usage.md`
  (canonical HOWTO), `scripts/run_pipeline.py` (thin CLI wrapper),
  `requirements.txt` pinned to `kbforge>=0.1.0,<1.0.0`.
- `expert/`: WorkBuddy expert package, structurally identical to B (§3 / §12-⑤) —
  reuses the same core orchestrator and the same `references/usage.md`; its own
  `requirements.txt` uses the same compatibility range.
- CI `smoke-core-api` now exercises the exact CLI surface B / expert invoke
  (make-fixtures → build → export → assert file), completing the §12-⑤ drift guard.
- README / CHANGELOG updated with the four-form architecture and compatibility pin.

[0.1.0]: https://github.com/example/kb-forge/releases/tag/v0.1.0
