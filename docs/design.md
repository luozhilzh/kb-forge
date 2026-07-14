# kb-forge Design

The canonical architecture and module layout for `kb-forge`. This document is
the in-repo companion to the planning rationale
([知识星球整理工具集_开源方案.md](知识星球整理工具集_开源方案.md)) and is kept in sync with the code.

---

# kb-forge 设计

`kb-forge` 的权威架构与模块布局。本文档是规划文档（[知识星球整理工具集_开源方案.md](知识星球整理工具集_开源方案.md)）的仓库内配套，并与代码保持同步。

## 1. Principles / 设计原则

- **Local-first, zero external dependency by default.** The core never requires
  an LLM or a vector DB. `enrich` (LLM) and `embedding` backends are optional
  and OFF by default.
- **本地优先、默认零外部依赖。** core 永不强制要求 LLM 或向量库。`enrich`（LLM）与
  `embedding` 后端均为可选、默认关闭。
- **One core, thin shells.** All real logic lives in `src/kbforge/core/`. Every
  other form is a thin wrapper that calls the core through the `kbforge` CLI
  (subprocess), pinned to `kbforge>=0.1.0,<1.0.0`.
- **一个核心 + 薄封装。** 所有真实逻辑都在 `src/kbforge/core/`。其余形态都是薄封装，
  通过 `kbforge` CLI（子进程）调用同一个 core，兼容区间钉在 `kbforge>=0.1.0,<1.0.0`。
- **OKF-compatible output.** The wiki is Markdown + YAML frontmatter; `type` is
  required and links are the knowledge graph.
- **产物对齐 OKF。** wiki 为 Markdown + YAML frontmatter，`type` 必填，链接即知识图谱。

## 2. Architecture: one core, four shells / 架构：一核四壳

```
                ┌──────────────────────────────────────────┐
                │            kbforge  CLI  (A)               │  python -m kbforge
                └───────────────────────┬────────────────────┘
                                         │ calls
                ┌────────────────────────┼────────────────────────┐
                │                        │                         │
        ┌───────▼──────┐        ┌───────▼──────┐         ┌────────▼───────┐
        │  B Skill     │        │  Expert pkg  │         │  C framework   │
        │ (WorkBuddy)  │        │ (WorkBuddy)  │         │  import kbforge│
        └───────┬──────┘        └───────┬──────┘         └────────┬───────┘
                └───────────┬───────────┘                          │
                         (all via `kbforge` CLI subprocess)        │
                                 └──────────────┬───────────────────┘
                                                 ▼
                                    ┌────────────────────────┐
                                    │   kbforge.core  (唯一真相源) │
                                    └────────────────────────┘
```

- **A — CLI** (`kbforge ...`): the `python -m kbforge` entry point.
- **B — WorkBuddy Skill** (`B-workbuddy-skill/`): drives core via the `kbforge`
  CLI subprocess; ships `SKILL.md` + `references/usage.md` + `scripts/run_pipeline.py`.
- **C — importable framework** (`kbforge` package + `adapters/`): for embedding in
  other Python code.
- **Expert — WorkBuddy expert package** (`expert/`): structurally identical to B;
  reuses the same core orchestrator and the same `references/usage.md`.

## 3. Module layout / 模块布局

```
src/kbforge/
├── cli.py                  # A: click commands (make-fixtures/build/export/query/site/validate/diff/enrich/mcp)
├── mcp_server.py           # MCP server (optional `mcp` dep): exposes core as standard MCP tools
├── config.py               # config contract (yaml + .env), PathsConfig, QueryConfig
├── frontmatter.py          # tiny YAML-frontmatter helper (no extra dep)
├── adapters/               # pluggable platform fetchers
│   ├── base.py             # PlatformAdapter ABC (fetch_topics/download_attachment/paginate)
│   ├── mock.py             # MockAdapter (tests)
│   ├── zsxq.py             # Zsxq adapter (wraps zsxq-cli)
│   ├── local_archive.py    # LocalArchiveAdapter (offline: reads an on-disk archive)
│   └── example_wechat.py   # skeleton adapter (no dead code, documents the interface)
├── core/
│   ├── pipeline.py         # run(): orchestrates ingest -> build_index
│   ├── archive_ingest.py   # ingest_archive(): local archive -> self-contained KB
│   ├── wiki/
│   │   ├── ingest.py       # post -> OKF wiki page (content_hash over body-only)
│   │   ├── build_index.py  # wiki/*.md -> index.md + .graph.json + .backlinks.json
│   │   └── schema.py       # SCHEMA.md topic parsing (advisory)
│   ├── exporters/          # pluggable output layer
│   │   ├── extract.py      # CaseBundle + extract_bundles(wiki_dir, types)
│   │   ├── base.py         # BaseExporter
│   │   ├── markdown.py     # MarkdownExporter
│   │   ├── pptx.py         # PptxExporter (python-pptx, built-in minimal template)
│   │   └── html.py         # HtmlExporter (self-contained HTML)
│   ├── query/              # RAG-ready retrieval
│   │   ├── base.py         # Retriever + Result (serializable) + registry
│   │   ├── bm25.py         # BM25 with CJK bigram tokenization (zero-dep)
│   │   ├── graph.py        # GraphRetriever (PPR over the link graph, α=0.85)
│   │   └── embedding.py    # EmbeddingRetriever (optional, OFF)
│   ├── site.py             # build_site(): wiki -> self-contained MkDocs project
│   ├── diff.py             # OKF anti-drift guard (validate + snapshot/diff)
│   └── enrich.py           # local claim anchoring (LLM OFF by default)
└── tools/
    └── make_fixtures.py    # synthetic KB generator (no real data)
```

## 4. Pipeline / 处理流水线

```
raw posts ──archive/ (year/month/t<topic_id>.md)──▶ ingest ──▶ wiki/*.md (OKF)
                                                              │
                                                build_index ─┤──▶ index.md
                                                              ├──▶ .graph.json (nodes+edges)
                                                              └──▶ .backlinks.json
                                                              │
                          ┌───────────────────────────────────┼───────────────────────┐
                          ▼                                   ▼                       ▼
                   exporters (pptx/md/html)              query (GraphRetriever)    site (MkDocs)
                   CaseBundle -> deliverables           RAG-ready retrieval        browsable + search
```

## 5. OKF contract / OKF 契约

- Each wiki page is `type: <concept|entity|case|pitfall|post>` + `title` +
  `sources` + `tags` + `content_hash`, with `[[wiki-link]]` syntax in the body.
- `index.md` (hub) and `log.md` (changelog) are reserved files.
- Consumption is tolerant: unknown `type`, missing optional fields, and dangling
  links are warnings, not hard errors (see `tests/test_okf_compliance.py`).
- 每个 wiki 页 = `type` + `title` + `sources` + `tags` + `content_hash`，正文用
  `[[wiki-link]]` 双链。
- `index.md`（枢纽）与 `log.md`（变更史）为保留文件。
- 本仓库的 OKF 规范说明见 [`SCHEMA.md`](../SCHEMA.md)（hub 编译时自动播种的 `SCHEMA.md` 与此同源）。
- 消费端容错：未知 type、缺失可选字段、断链均视为告警而非硬错（见
  `tests/test_okf_compliance.py`）。

## 6. Retrieval / 检索（RAG 就绪）

- `GraphRetriever` (default): undirected uniform graph from `[[links]]` → BM25
  lexical seed → Personalized PageRank (α=0.85) → sparse fallback to pure BM25.
  Deterministic, zero embedding cost.
- `BM25`: dependency-free, CJK bigram tokenization.
- `EmbeddingRetriever`: optional backend, OFF by default; lazy-loads a user
  supplied embedder + vector store. Never imported by CI.
- `Result` is fully serializable (`to_dict`), so `kbforge query --format json`
  is MCP-friendly.
- `GraphRetriever`（默认）：由 `[[links]]` 建无向均匀图 → BM25 词法种子 →
  个性化 PageRank（α=0.85）→ 稀疏兜底退纯 BM25。确定、零 embedding 成本。
- `BM25`：零依赖，CJK 用 bigram 分词。
- `EmbeddingRetriever`：可选后端，默认 OFF，懒加载用户自备向量库，CI 不触。
- `Result` 完全可序列化（`to_dict`），故 `kbforge query --format json` 对 MCP 友好。

## 7. Site generation / 站点生成

`build_site()` rewrites `[[slug]]` / `[[slug|label]]` into real
`[label](slug.md)` links at **generate time**, so the output builds with
**stock MkDocs** — no custom hook, no extra dependency. It emits
`docs/<slug>.md` + `docs/index.md` (type-grouped) + `mkdocs.yml` (material theme
+ `search` plugin + type-grouped `nav`). Unknown slugs are kept literal (never a
broken link). `kbforge site --build` runs `mkdocs build` best-effort.

`build_site()` 在**生成期**就把 `[[slug]]`/`[[slug|label]]` 改写成真实
`[label](slug.md)` 链接，因此产物用**原版 MkDocs** 即可构建——无需自定义
hook、零额外依赖。产出 `docs/<slug>.md` + `docs/index.md`（按 type 分组）+
`mkdocs.yml`（material 主题 + `search` 插件 + type 分组 `nav`）。未知 slug 保留原样
（绝不产出断链）。`kbforge site --build` 尽力调用 `mkdocs build`。

## 7.5 Enrich + Diff / 增强与防漂移守卫

**`enrich` — claim-level source anchoring (local-first, LLM optional).**
`enrich_wiki(wiki_dir, strategy)` splits each wiki page into candidate claims
(sentences) and attaches the page's `source_anchor` (its `sources` frontmatter),
so a downstream RAG retriever can cite *which source post a claim came from*, not
just which page. The MVP ships `LocalClaimExtractor` (zero-dep, deterministic:
keeps a sentence when it carries a wiki-link, a number/metric, a definition cue,
or sufficient length). `EnrichmentStrategy` is the ABC; `NoOpStrategy` is the
default; an LLM-based strategy is a documented, OFF-by-default extension point
(mirrors `EmbeddingRetriever`).

**`diff` — OKF anti-drift guard.**
`validate_wiki(wiki_dir)` checks a single compiled wiki against the OKF contract
(every page must carry `type` + `content_hash`; every `[[wiki-link]]` must
resolve). `diff_wiki(wiki_dir)` compares the current wiki against a saved baseline
snapshot (`<wiki>/.wiki_snapshot.json`, created on first run) and reports added /
removed / changed pages, broken links, orphaned references, and contract
violations. Re-run it after every re-ingest to catch knowledge-base drift before
it reaches RAG. All report types expose `to_dict()` for MCP-friendly output.

**`enrich` —— claim 级来源锚定（本地优先、LLM 可选）。**
`enrich_wiki(wiki_dir, strategy)` 把每页切成候选 claim（句子），并附上该页的
`source_anchor`（其 `sources` frontmatter），让下游 RAG 检索器能回溯**某条 claim
来自哪个源帖**，而不只是哪一页。MVP 自带 `LocalClaimExtractor`（零依赖、确定性：句子
含 wiki 链接 / 数字指标 / 定义线索或足够长即保留）。`EnrichmentStrategy` 为抽象基类，
`NoOpStrategy` 为默认，LLM 策略是文档化、默认 OFF 的扩展点（与 `EmbeddingRetriever` 同套路）。

**`diff` —— OKF 防漂移守卫。**
`validate_wiki(wiki_dir)` 对单态编译后 wiki 做 OKF 契约校验（每页须带 `type` +
`content_hash`；每条 `[[wiki-link]]` 须可解析）。`diff_wiki(wiki_dir)` 把当前 wiki 与
已存基线快照（`<wiki>/.wiki_snapshot.json`，首次运行自动建立）对比，报告新增/删除/变更页、
断链、孤儿引用、契约违规。每次重抓后重跑，即可在漂移进入 RAG 前抓住。所有报告类型均提供
`to_dict()` 以对 MCP 友好。

## 7.6 MCP server / MCP 服务

The product closure of the RAG pipeline. `src/kbforge/mcp_server.py` exposes the
local-first core as **standard MCP tools** so any LLM agent can forge + query a
knowledge base without leaving its loop. It is **not** a fifth shell — it is a
thin wrapper that calls the same core functions as the CLI.

**Tools registered:** `query` / `export` / `build_site` / `enrich` / `validate` /
`diff` / `build`. Each returns serializable data (list/dict shapes identical to
the `--format json` CLI output).

**Optional dependency, lazy import.** `mcp` is declared in
`[project.optional-dependencies]` (`pip install 'kbforge[mcp]'`). The module's
tool functions import only `core`, so the base install and the functions remain
importable without `mcp`; the `FastMCP` server is built lazily inside
`create_server()`. The CLI `kbforge mcp [--transport stdio|sse]` lazy-imports the
server, so the CLI itself never requires `mcp`.

**Zero runtime model/vector cost.** The server wraps the same zero-dependency
local tools as the CLI/B/Expert — no external LLM or vector store is touched.
This keeps the "local-first, external-model-deferred" principle intact even when
the toolkit is consumed as an agent tool.

## 7.6 MCP server / MCP 服务

RAG 流水线的产品闭环。`src/kbforge/mcp_server.py` 把本地优先 core 暴露成**标准 MCP
工具**，让任意 LLM agent 不必跳出自身循环即可「锻造 + 检索」知识库。它**不是**第五个壳——
只是一个薄封装，调用的还是与 CLI 相同的 core 函数。

**注册的工具：** `query` / `export` / `build_site` / `enrich` / `validate` / `diff` /
`build`。每个工具都返回可序列化数据（与 CLI `--format json` 完全同构的 list/dict 形状）。

**可选依赖、懒加载。** `mcp` 声明在 `[project.optional-dependencies]`（`pip install
'kbforge[mcp]'`）。模块的工具函数只 import `core`，因此基础安装与函数在其缺失时仍可用；
`FastMCP` server 在 `create_server()` 内懒加载。CLI 的 `kbforge mcp [--transport
stdio|sse]` 懒加载该 server，故 CLI 自身绝不依赖 `mcp`。

**运行时零模型/向量成本。** server 包装的与 CLI/B/Expert 是同一套零依赖本地工具——绝不碰
外部 LLM 或向量库。即使以 agent 工具形态被消费，「本地优先、外部模型后置」原则依然成立。

## 7.7 Real-data ingest: LocalArchiveAdapter / 真实 archive 接入

The bridge from "synthetic fixtures" to "your real community posts". You already
have a downloaded archive on disk; `LocalArchiveAdapter` turns it into a
self-contained KB **without touching any platform API** (no zsxq-cli, no token).

- `LocalArchiveAdapter(root)` reads `<year>/<month>/<date>-t<topic_id>.md` posts,
  cleans zsxq inline `<e .../>` tags, derives the numeric `topic_id` from the
  filename, and maps frontmatter (`title`/`author`/`date`/`tags`) into `Topic`
  objects. `scan(year, month, limit)` slices the archive.
- `ingest_archive(source, out, *, year, month, limit, dry_run)` writes normalized
  OKF posts into `<out>/archive/<year>/<month>/`, seeds `SCHEMA.md` with the
  discovered tags, then calls `run()` to compile the wiki. The output is
  byte-for-byte the same layout `make-fixtures` produces, so `query` / `site` /
  `export` / `enrich` / `diff` / `mcp` all work unchanged.
- CLI: `kbforge ingest-archive --source <archive> --out <kb-root> [--year 2026]
  [--month 07] [--limit N] [--dry-run]`.
- Real posts carry no `[[wiki-link]]`, so the link graph has no edges; `query`
  transparently falls back to BM25 (lexical) retrieval — no extra setup.

**真实数据接入：LocalArchiveAdapter。** 把工具从「合成 fixtures 验证」变成「真正整理你自己的
社群帖」的桥。你本机已下载好 archive，`LocalArchiveAdapter` 把它变成自包含 KB，**不碰任何平台
API**（不调 zsxq-cli、不需要 token）。

- `LocalArchiveAdapter(root)` 读 `<year>/<month>/<date>-t<topic_id>.md` 帖，清洗 zsxq 的
  `<e .../>` 内联标签，从文件名抽数字 `topic_id`，把 frontmatter（`title`/`author`/`date`/`tags`）
  映射成 `Topic`。`scan(year, month, limit)` 可切片。
- `ingest_archive(source, out, *, year, month, limit, dry_run)` 把归一化 OKF 帖写入
  `<out>/archive/<year>/<month>/`，用扫描到的标签自动播种 `SCHEMA.md`，再调 `run()` 编译 wiki。
  产物与 `make-fixtures` 字节级同构，故 `query`/`site`/`export`/`enrich`/`diff`/`mcp` 原样可用。
- CLI：`kbforge ingest-archive --source <archive> --out <kb-root> [--year 2026]
  [--month 07] [--limit N] [--dry-run]`。
- 真实帖不含 `[[wiki-link]]`，故链接图无边；`query` 自动退 BM25（词法）检索——无需额外配置。

## 8. Compatibility pin / 兼容区间

All thin shells (B, Expert) declare `kbforge>=0.1.0,<1.0.0`. The upper bound
means a 1.0 API break fails **loudly** (install error) instead of silently
breaking the shell (design doc §12-⑤). CI runs a B-invoked CLI smoke test to
catch core↔shell drift.

所有薄封装（B、Expert）声明 `kbforge>=0.1.0,<1.0.0`。上界意味着 1.0 改 API 会
**安装即失败告警**，而非静默破坏封装（设计文档 §12-⑤）。CI 跑 B 调用的 CLI 冒烟测试
抓 core↔封装 漂移。

## 9. CI / 持续集成

Dual matrix (Ubuntu + Windows) × Python 3.11/3.12/3.13 runs `pytest -m "not e2e"`.
`@pytest.mark.e2e` tests (network / real credentials) run on Ubuntu only.
`.gitattributes` forces `eol=lf`. A `smoke-core-api` job exercises the exact CLI
surface B / the expert invoke.

双矩阵（Ubuntu + Windows）× Python 3.11/3.12/3.13 跑 `pytest -m "not e2e"`。
`@pytest.mark.e2e`（网络/真实凭证）仅 Ubuntu 跑。`.gitattributes` 强制 `eol=lf`。
`smoke-core-api` 作业跑 B/专家实际调用的 CLI 链做漂移守卫。

## 10. Status / 当前状态

**Implemented (done, tested):**
- Phase 0 skeleton: packaging, config contract, adapter abstraction, synthetic
  fixtures, OKF golden test.
- Exporters: CaseBundle + Markdown / PPTX / HTML.
- Delivery forms B (Skill) + Expert package.
- Retrieval: `query` / `GraphRetriever` (PPR) + BM25 + EmbeddingRetriever (OFF).
- Publish: `site` / MkDocs generator.
- **Real-data ingest:** `LocalArchiveAdapter` (offline) + `ingest_archive`
  (archive on disk -> self-contained KB; no platform API).
- **`enrich`** (local claim anchoring; LLM strategy OFF by default).
- **`diff`** (OKF anti-drift guard: `validate` + snapshot/diff after re-ingest).
- **MCP server** (`kbforge mcp`, exposes query/export/build_site/enrich/validate/
  diff/build as standard MCP tools; optional `mcp` dependency, zero runtime
  model/vector cost).

**Deferred (not in MVP):**
- `enrich` LLM strategy (interface implemented, OFF by default).
- `dedupe` cross-post merge.
- Five page types (extend concept/entity/case/pitfall with scheme/comparison).

**已实现（已测试）：**
- Phase 0 骨架：打包、配置契约、adapter 抽象、合成 fixtures、OKF golden 测试。
- 导出族：CaseBundle + Markdown / PPTX / HTML。
- 交付形态 B（Skill）+ 专家包。
- 检索：`query` / `GraphRetriever`（PPR）+ BM25 + EmbeddingRetriever（OFF）。
- 发布：`site` / MkDocs 生成器。
- **真实数据接入**：`LocalArchiveAdapter`（离线）+ `ingest_archive`（本机 archive
  → 自包含 KB；不调平台 API）。
- **`enrich`**（本地 claim 锚源；LLM 策略默认 OFF）。
- **`diff`**（OKF 防漂移守卫：`validate` + 重抓后快照对比）。
- **MCP server**（`kbforge mcp`，把 query/export/build_site/enrich/validate/diff/
  build 暴露成标准 MCP 工具；`mcp` 为可选依赖，运行时零模型/向量成本）。

**延后（不在 MVP）：**
- `enrich` 的 LLM 策略（接口已就位，默认 OFF）。
- `dedupe` 跨帖合并。
- 五类页面（在 concept/entity/case/pitfall 基础上扩 scheme/comparison）。
