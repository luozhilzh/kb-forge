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

[0.1.0]: https://github.com/example/kb-forge/releases/tag/v0.1.0
