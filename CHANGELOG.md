# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/) and this project adheres to
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- **`classify`** command + OKF five-class auto-classification (feature ③, the
  knowledge-base *structure* layer): turns a flat pile of `post` pages into a
  typed KB (`concept/entity/case/pitfall/scheme/comparison/post`).
  - `LocalClassifier`: deterministic, zero-dependency scorer (tag overlap +
    heading/structural signals + weak body cue; `entity` fires only on explicit
    title/heading/tag naming to avoid false positives).
  - `LLMClassifier`: optional OpenAI-compatible enhancement (stdlib `urllib`
    only, no SDK); transparently falls back to `local` on missing key / error.
  - Type set, lexicon and structural rules are **user-configurable** via
    `config.yaml` → `classify:` (merged over defaults), so the product works
    for *any* domain, not hardcoded to one.
  - `classify --wiki-dir X --dry-run` previews the per-type distribution; the
    real run writes `type` back and rebuilds `index.md`.
  - `ClassifyConfig` lives in a leaf module to avoid a core↔config import cycle.

- **Richer `sample_kb` demo fixture** (`tests/fixtures/sample_kb/archive`): expanded
  from 3 to 9 synthetic posts so the bundled KB now exercises **all seven** OKF
  types (`case/pitfall/scheme/comparison/concept/entity/post`). The e2e test now
  also asserts the sample covers the six main typed classes, so a regression that
  shrinks the demo's type coverage fails CI.

- **End-to-end pipeline test** (`tests/test_e2e_pipeline.py`): forges the bundled
  `sample_kb` archive from scratch and asserts the full
  `ingest-archive → classify → enrich → export → query → validate` chain produces
  a structured, queryable, OKF-compliant KB. Pure-local (no network / API / key),
  so it runs on every CI push and closes the integration gap unit tests miss.

- **`dedupe`** command + cross-source duplicate detection (feature ④): collapses
  repeats pulled from a platform (re-shares, cross-group reposts, double captures)
  without touching user data.
  - `dedupe_pages(dir)`: recursively scans `*.md`, groups pages by a sha256 of the
    normalized **body only** (same normalization as `wiki/ingest.content_hash`, so
    cross-layer hashes match), and for each collision marks redundant pages with
    `duplicate_of: <canonical-slug>`; the canonical is the earliest `published_at`
    (tie-broken by slug). Every page also gets a `content_hash` filled in if missing.
  - `mark` strategy (default): **non-destructive** — only frontmatter metadata is
    appended/updated, bodies are never edited and files are never removed.
  - `merge` (physically collapse/relocate duplicates) is a documented, OFF-by-default
    extension point, intentionally left out of the MVP so callers never lose data.
  - `dedupe <dir> --dry-run` previews the report (total / unique / duplicate groups /
    duplicates / to_write) as JSON.

- **`enrich` `llm` strategy wired** (completes feature ②'s optional enhancement):
  `LLMEnrichmentStrategy` now calls an OpenAI-compatible `/chat/completions`
  endpoint with **stdlib `urllib` only** (no SDK), asks the model to return a JSON
  array of concise claims, and **transparently falls back to `LocalClaimExtractor`
  on missing key / network error / unparseable response**. The network boundary is
  isolated in `_post_chat_completion` for testing. `enrich --strategy llm` is
  OFF-by-default and reads its key from `config.yaml` `enrich.llm` or the
  `LLM_API_KEY` env var. This makes the README's "LLM strategy OFF by default"
  claim actually true.

- **Ingest data-noise cleaning + `clean` command** (feature ⑤, data-quality
  layer): real paid-community exports (e.g. Zsxq) carry a `## 摘要` section that
  is almost always a *truncated, redundant preview* of the body — it repeats the
  opening of `## 正文` and ends mid-sentence with an ellipsis, which previously
  leaked into PPT / HTML summaries and duplicated body content.
  - `core/clean.py`: `clean_summary_section` removes a `## 摘要` section when it
    is a clipping of the body (verbatim containment, prefix, or fuzzy
    near-substring via a sliding window over the normalized body — so a typo like
    `GPT4` vs `GPT-4` still matches); a *genuinely distinct* summary is kept and
    only a trailing truncation marker is stripped, so unique content is never
    silently deleted. Deterministic, dependency-free, idempotent.
  - Wired into `LocalArchiveAdapter._clean_body`, so every `ingest-archive` now
    produces clean OKF posts automatically.
  - `clean_post_body` is the single entry point, so further body cleaners can be
    added without touching callers.
  - `clean <dir>` CLI command: recursively scans `*.md` (skips
    `index.md`/`log.md`/`SCHEMA.md`), reports what would change, and rewrites
    in place only with `--apply` (frontmatter left byte-for-byte). Defaults to a
    safe dry-run.
  - Exporter `_first_paragraph` (the derived summary used by PPT / HTML / MD
    exporters) now skips markdown heading lines and bare image embeds, so slides
    show clean prose instead of a `## 正文` heading.
  - Verified on the real 370-post KB: a dry-run reports **369/370 redundant
    `## 摘要` sections removed** (the 1 remainder is a genuinely distinct
    summary, correctly preserved).

### Fixed
- `frontmatter.parse` now tolerates archive titles starting with YAML illegal
  indicators (`@`, `#`) by auto-quoting the offending scalar line, instead of
  crashing or silently dropping the title.
- `export` / `query` / `site` / `validate` / `diff` / `enrich` no longer require
  a `config.yaml` in cwd when an explicit `--wiki-dir` is given (`load_config`
  gains a `require` flag); self-contained wikis (e.g. from `ingest-archive`)
  run directly.

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

### Added (Phase 4 guard: enrich + diff)
- `core/diff.py`: OKF anti-drift guard.
  - `validate_wiki(wiki_dir)` — single-state OKF compliance (every page must
    carry `type` + `content_hash`; every `[[wiki-link]]` must resolve).
  - `diff_wiki(wiki_dir, before_dir=None)` — compares against a saved baseline
    snapshot (`<wiki>/.wiki_snapshot.json`, created on first run) and reports
    added / removed / changed pages, broken links, orphaned refs, and contract
    violations. Re-run after each re-ingest to catch KB drift.
  - `WikiSnapshot` / `DiffReport` / `Violation` are all serializable (`to_dict`).
- `core/enrich.py`: local-first claim enrichment (no LLM required).
  - `EnrichmentStrategy` ABC + `NoOpStrategy` (default) + `LocalClaimExtractor`
    (zero-dep, deterministic sentence/claim splitter that attaches each claim's
    `source_anchor`). An LLM strategy is a documented, OFF-by-default extension
    point (mirrors `EmbeddingRetriever`).
  - `enrich_wiki(wiki_dir, strategy)` returns `slug -> [claim dict]`.
- Three new CLI commands: `kbforge validate`, `kbforge diff`, `kbforge enrich
  [--strategy local|none]`; all support `--format json` (MCP-friendly).
- Golden tests: `test_diff.py` + `test_enrich.py` (validation, snapshot
  round-trip, compare add/remove/change, baseline creation; noop vs local
  extraction, source anchor, short-sentence skip, dict shape).

### Added (Phase 4 closure: MCP server)
- `src/kbforge/mcp_server.py`: exposes the local-first core as **standard MCP
  tools** so any LLM agent can forge + query a knowledge base in-loop. Tools:
  `query` / `export` / `build_site` / `enrich` / `validate` / `diff` / `build`.
  Every tool returns serializable data (list/dict shapes identical to the
  `--format json` CLI output).
- `mcp` is an **optional** dependency (`pip install 'kbforge[mcp]'`); the base
  install and the tool functions remain importable without it (`mcp` is imported
  lazily inside `create_server`). The server wraps the same zero-dependency local
  tools — no external model or vector store is touched at runtime.
- `mcp` CLI command: `kbforge mcp [--transport stdio|sse]` (stdio is the default
  for local agents). CLI stays usable without the `mcp` extra (lazy import).
- `mcp` added to `[project.optional-dependencies]` and to the `dev` extra so CI
  covers the registration guard.
- Golden tests: `test_mcp.py` (tool functions on a built wiki — query/validate/
  enrich/diff/export/build_site/build; plus a registration guard that asserts
  all 7 tool names are wired up, skipped where `mcp` is not installed).

### Added (real-data: local archive ingest)
- `adapters/local_archive.py`: `LocalArchiveAdapter` — reads an on-disk archive
  (`<year>/<month>/<date>-t<topic_id>.md`) **offline**, with no external API.
  It cleans zsxq inline `<e .../>` tags, derives the numeric `topic_id` from the
  filename, maps frontmatter (`title`/`author`/`date`/`tags`) into `Topic`
  objects, and supports `scan(year, month, limit)` filtering. Registered as the
  `local-archive` platform in `ADAPTERS`.
- `core/archive_ingest.py`: `ingest_archive(source, out, *, year, month, limit,
  dry_run)` — the end-to-end offline path. It writes normalized OKF posts into
  `<out>/archive/<year>/<month>/` (replicating the source layout), seeds
  `SCHEMA.md` with the discovered tags (so validation stays quiet), then calls
  `run()` to compile the wiki. Output is a self-contained KB root identical to
  `make-fixtures`, so every downstream stage works unchanged.
- `ingest-archive` CLI command: `kbforge ingest-archive --source <archive>
  --out <kb-root> [--year 2026] [--month 07] [--limit N] [--dry-run]`. Offline;
  no credentials, no network.
- Golden tests: `test_local_archive.py` (adapter scan/clean/tag-derive, year/
  month/limit filters, end-to-end wiki build with no inline tags, auto-seeded
  SCHEMA tags, dry-run writes nothing).


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

### 新增（Phase 4 守卫：enrich + diff）
- `core/diff.py`：OKF 防漂移守卫。
  - `validate_wiki(wiki_dir)`——单态 OKF 合规校验（每页须带 `type` + `content_hash`；
    每条 `[[wiki-link]]` 必须可解析）。
  - `diff_wiki(wiki_dir, before_dir=None)`——与已存基线快照（`<wiki>/.wiki_snapshot.json`，
    首次运行自动建立）对比，报告新增/删除/变更页、断链、孤儿引用、契约违规。每次
    重抓后重跑即可抓 KB 漂移。
  - `WikiSnapshot` / `DiffReport` / `Violation` 均可序列化（`to_dict`）。
- `core/enrich.py`：本地优先的 claim 增强（无需 LLM）。
  - `EnrichmentStrategy` ABC + `NoOpStrategy`（默认）+ `LocalClaimExtractor`
    （零依赖、确定性的句子/claim 切分器，给每条 claim 附 `source_anchor`）。LLM 策略
    是文档化的、默认 OFF 的扩展点（与 `EmbeddingRetriever` 同套路）。
  - `enrich_wiki(wiki_dir, strategy)` 返回 `slug -> [claim dict]`。
- 三个新 CLI：`kbforge validate`、`kbforge diff`、`kbforge enrich [--strategy
  local|none]`；均支持 `--format json`（对 MCP 友好）。
- Golden 测试：`test_diff.py` + `test_enrich.py`（校验、快照往返、增删改对比、基线创建；
  noop vs 本地抽取、来源锚点、短句过滤、字典形状）。

### 新增（Phase 4 闭环：MCP server）
- `src/kbforge/mcp_server.py`：把本地优先 core 暴露成**标准 MCP 工具**，让任意 LLM
  agent 在自身循环内「锻造 + 检索」知识库。工具：`query` / `export` / `build_site` /
  `enrich` / `validate` / `diff` / `build`。每个工具都返回可序列化数据（与 CLI
  `--format json` 完全同构的 list/dict 形状）。
- `mcp` 是**可选**依赖（`pip install 'kbforge[mcp]'`）；基础安装与工具函数在其缺失时
  仍可用（`mcp` 在 `create_server` 内懒加载）。server 包装的还是那套零依赖本地工具——
  运行时绝不碰外部模型或向量库。
- `mcp` CLI 命令：`kbforge mcp [--transport stdio|sse]`（stdio 为本地 agent 默认）。
  CLI 在未装 `mcp` extra 时仍可用（懒加载）。
- `mcp` 加入 `[project.optional-dependencies]` 及 `dev` extra，使 CI 覆盖注册守卫。
- Golden 测试：`test_mcp.py`（在已编译 wiki 上的工具函数——query/validate/enrich/diff/
  export/build_site/build；外加注册守卫断言 7 个工具名全部接上，未装 `mcp` 时跳过）。

### 新增（真实数据：本地 archive 接入）
- `adapters/local_archive.py`：`LocalArchiveAdapter`——**离线**读取本机 archive
  （`<year>/<month>/<date>-t<topic_id>.md`），不调任何外部 API。清洗 zsxq 的 `<e .../>`
  内联标签、从文件名抽数字 `topic_id`、把 frontmatter（`title`/`author`/`date`/`tags`）
  映射成 `Topic`，并支持 `scan(year, month, limit)` 切片过滤。已注册为 `local-archive` 平台。
- `core/archive_ingest.py`：`ingest_archive(source, out, *, year, month, limit,
  dry_run)`——离线端到端路径。把归一化 OKF 帖写入 `<out>/archive/<year>/<month>/`
  （复刻源目录结构），用扫描到的标签自动播种 `SCHEMA.md`（让校验静默），再调 `run()`
  编译 wiki。产物是和 `make-fixtures` 同构的自包含 KB root，下游所有阶段原样可用。
- `ingest-archive` CLI 命令：`kbforge ingest-archive --source <archive>
  --out <kb-root> [--year 2026] [--month 07] [--limit N] [--dry-run]`。离线；
  无凭证、无网络。
- Golden 测试：`test_local_archive.py`（适配器 scan/清洗/抽 id、year/month/limit
  过滤、端到端 wiki 构建且无内联标签、自动播种 SCHEMA 标签、dry-run 不落盘）。

