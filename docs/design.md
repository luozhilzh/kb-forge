# kb-forge Design

The canonical architecture and module layout for `kb-forge`. This document is
the in-repo companion to the planning rationale
(`知识星球整理工具集_开源方案.md`) and is kept in sync with the code.

---

# kb-forge 设计

`kb-forge` 的权威架构与模块布局。本文档是规划文档（`知识星球整理工具集_开源方案.md`）的仓库内配套，并与代码保持同步。

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
├── cli.py                  # A: click commands (make-fixtures/build/export/query/site)
├── config.py               # config contract (yaml + .env), PathsConfig, QueryConfig
├── frontmatter.py          # tiny YAML-frontmatter helper (no extra dep)
├── adapters/               # pluggable platform fetchers
│   ├── base.py             # PlatformAdapter ABC (fetch_topics/download_attachment/paginate)
│   ├── mock.py             # MockAdapter (tests)
│   ├── zsxq.py             # Zsxq adapter (wraps zsxq-cli)
│   └── example_wechat.py   # skeleton adapter (no dead code, documents the interface)
├── core/
│   ├── pipeline.py         # run(): orchestrates ingest -> build_index
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
│   └── site.py             # build_site(): wiki -> self-contained MkDocs project
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

**Deferred (not in MVP):**
- `enrich` LLM layer (interface kept, default OFF).
- `diff` contradiction detection / incremental update guard.
- `dedupe` cross-post merge.
- Five page types (extend concept/entity/case/pitfall with scheme/comparison).
- MCP server (Phase 4; query output already MCP-friendly).

**已实现（已测试）：**
- Phase 0 骨架：打包、配置契约、adapter 抽象、合成 fixtures、OKF golden 测试。
- 导出族：CaseBundle + Markdown / PPTX / HTML。
- 交付形态 B（Skill）+ 专家包。
- 检索：`query` / `GraphRetriever`（PPR）+ BM25 + EmbeddingRetriever（OFF）。
- 发布：`site` / MkDocs 生成器。

**延后（不在 MVP）：**
- `enrich` LLM 层（接口保留，默认 OFF）。
- `diff` 矛盾检测 / 增量更新守卫。
- `dedupe` 跨帖合并。
- 五类页面（在 concept/entity/case/pitfall 基础上扩 scheme/comparison）。
- MCP server（Phase 4；query 输出已对 MCP 友好）。
