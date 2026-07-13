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

### Added (Phase 3 retrieval: query / RAG-readiness)
- `core/query/`: backend-agnostic retriever layer.
  - `GraphRetriever` (MVP default): Personalized PageRank over the `[[wiki-link]]`
    graph — undirected uniform graph → BM25 lexical seed → PPR (α=0.85) power
    iteration → sparse fallback to pure BM25. Zero embedding cost, deterministic.
  - `BM25`: dependency-free scorer with CJK bigram tokenization (zero-dep, per P2 decision).
  - `EmbeddingRetriever`: optional, OFF by default; lazy-loads a user-supplied
    embedder + vector store (never imported by CI). Extension point only.
  - `Result` is fully serializable (MCP-friendly, per §5.7 / §12-④).
- `query` CLI command: `kbforge query "<text>" [--top-k N] [--backend graph|embedding]
  [--format text|json]`; `--format json` emits the serializable results.
- Golden tests: `test_query.py` (tokenize bigram, GraphRetriever ranking, BM25
  fallback, registry, embedding-unconfigured guard, context shape).

### Added (Phase 3 publish: MkDocs site)
- `core/site.py`: `build_site(wiki_dir, out_dir, *, site_name, theme, build)` turns a
  compiled wiki into a **self-contained MkDocs project**. `[[wiki-link]]` /
  `[[wiki-link|label]]` is rewritten to a real `[label](slug.md)` link at *generate*
  time, so the output builds with **stock MkDocs** — no custom hook, no extra
  dependency. Emits a type-grouped `nav` + the built-in `search` plugin.
- `site` CLI command: `kbforge site --kb-root X [--out DIR] [--site-name NAME]
  [--theme material|readthedocs|mkdocs] [--build/--no-build]`; `--build` runs
  `mkdocs build` only when `mkdocs` is on PATH (best-effort, never required).
- `kbforge` itself stays MkDocs-free: the generated site is plain MkDocs, so any
  theme the user has installed works (`material` needs `mkdocs-material`).
- Golden tests: `test_site.py` (project emitted, links resolved, unknown slug kept
  literal, valid grouped `mkdocs.yml`, landing index, unsupported-theme guard).

[0.1.0]: https://github.com/example/kb-forge/releases/tag/v0.1.0

---

## 中文变更记录（Chinese Changelog）

## [0.1.0] - 2026-07-13

### 新增
- Phase 0 骨架：打包配置、配置契约、adapter 抽象。
- 合成 fixtures 生成器（`make-fixtures`）+ 隔离的 `tests/fixtures/`。
- OKF v0.1 合规 golden 测试（`test_okf_compliance.py`）。
- 极简流水线：`config -> mock adapter -> ingest (content_hash) -> build_index`，
  产出 OKF 兼容的 wiki。
- `MarkdownExporter`（极简），演示可插拔输出层。
- CI：双矩阵（Ubuntu + Windows）pytest，e2e 仅跑 Ubuntu。

### 新增（Phase 2 导出族）
- `extract.py`：`CaseBundle` 数据类 + `extract_bundles(wiki_dir)`，读取已编译
  wiki 页面（`type` 过滤，默认 `case/pitfall/concept`），产出与导出器无关的 bundle。
- `PptxExporter`：内置极简模板（不依赖外部 .pptx），经 `python-pptx` 生成
  标题页 + 每 bundle 一页。
- `HtmlExporter`：独立自含 HTML，每 bundle 一个 `<section>`（HTML 转义）。
- `export` CLI 命令：`kbforge export --format pptx|html|md [--types ...] [--out ...]`。
- Golden 测试：`test_exporters.py`（bundle 结构 + pptx/html 往返 + md）。

### 新增（Phase 2 交付形态：B Skill + 专家包）
- `B-workbuddy-skill/`：WorkBuddy Skill——`SKILL.md`（触发词 + 经 `kbforge` CLI
  子进程驱动 core + 合规红线）、`references/usage.md`（权威 HOWTO）、
  `scripts/run_pipeline.py`（薄封装）、`requirements.txt` 钉 `kbforge>=0.1.0,<1.0.0`。
- `expert/`：WorkBuddy 专家包，与 B 同构（§3 / §12-⑤）——复用同一 core 编排器与
  同一 `references/usage.md`；各自的 `requirements.txt` 用相同兼容区间。
- CI `smoke-core-api` 现跑 B/专家实际调用的 CLI 链（make-fixtures → build →
  export → 断言文件），完成 §12-⑤ 漂移守卫。
- README / CHANGELOG 同步四形态架构与兼容区间。

### 新增（Phase 3 检索：query / RAG 就绪）
- `core/query/`：后端无关的检索层。
  - `GraphRetriever`（MVP 默认）：在 `[[wiki-link]]` 链接图上做个性化 PageRank——
    无向均匀图 → BM25 词法种子 → PPR（α=0.85）幂迭代 → 稀疏兜底退纯 BM25。
    零 embedding 成本、确定可复现。
  - `BM25`：零依赖打分器，CJK bigram 分词（按 P2 决策零依赖）。
  - `EmbeddingRetriever`：可选，默认 OFF，懒加载用户自备 embedder + 向量库
    （CI 绝不 import）。仅扩展点。
  - `Result` 完全可序列化（对 MCP 友好，见 §5.7 / §12-④）。
- `query` CLI 命令：`kbforge query "<文本>" [--top-k N] [--backend graph|embedding]
  [--format text|json]`；`--format json` 输出可序列化结果。
- Golden 测试：`test_query.py`（bigram 分词、GraphRetriever 排序、BM25 兜底、
  注册表、embedding 未配置守卫、context 形状）。

### 新增（Phase 3 发布：MkDocs 站点）
- `core/site.py`：`build_site(wiki_dir, out_dir, *, site_name, theme, build)` 把
  已编译 wiki 转成**自含 MkDocs 工程**。`[[wiki-link]]` / `[[wiki-link|label]]` 在
  **生成期**即改写为真实 `[label](slug.md)` 链接，故产物用**原版 MkDocs** 即可构建
  （无需自定义 hook、零额外依赖）。产出按 type 分组的 `nav` + 内置 `search` 插件。
- `site` CLI 命令：`kbforge site --kb-root X [--out DIR] [--site-name NAME]
  [--theme material|readthedocs|mkdocs] [--build/--no-build]`；`--build` 仅在
  `mkdocs` 在 PATH 上时才跑 `mkdocs build`（尽力而为，从不强制要求）。
- `kbforge` 自身保持不依赖 MkDocs：生成的站点是普通 MkDocs 工程，用户装了任意
  主题都能用（`material` 需 `mkdocs-material`）。
- Golden 测试：`test_site.py`（生成工程、链接解析、未知 slug 保留原样、合法分组
  `mkdocs.yml`、落地页、不支持主题守卫）。

[0.1.0]: https://github.com/example/kb-forge/releases/tag/v0.1.0
