# kb-forge

> Forge raw paid-community posts (e.g. Zsxq / 知识星球) into a structured, **OKF-compatible** knowledge base — then emit multi-format outputs including a case-study **PPT**.

[中文](#中文说明) · [English](#english)

---

## English

`kb-forge` is a local-first, zero-dependency-by-default toolkit that turns a stream of community posts into a clean knowledge base and reusable deliverables:

- **Pull** posts from a platform via a pluggable `PlatformAdapter` (Zsxq shipped; add your own).
- **Organize** raw posts into a year/month archive with stable `t<topic_id>` filenames.
- **Compile a wiki** (concept / entity / case / pitfall pages) with mechanical + optional LLM enrichment — every claim anchored to its source.
- **Extract** cases & pitfalls into a structured `CaseBundle`, then **export** to PPT / Markdown / HTML.
- **Publish** the wiki as a browsable, searchable **MkDocs site** — `[[wiki-link]]` is resolved at generate time, so it builds with stock MkDocs (zero extra deps).
- **Output is OKF-compatible** (Google *Open Knowledge Format* v0.1): Markdown + YAML frontmatter, `type` required, links = knowledge graph.

### Install

```bash
pip install -e ".[dev]"
```

### Quick start

```bash
# Generate a synthetic demo knowledge base (no real data, safe to commit)
python -m kbforge make-fixtures --out tests/fixtures/sample_kb

# Build the wiki from a knowledge root
kbforge build --kb-root tests/fixtures/sample_kb --dry-run   # preview
kbforge build --kb-root tests/fixtures/sample_kb             # write

# Pick a stage / profile
kbforge build --profile work --stage wiki --topic t123

# Extract cases from the built wiki and export to a deliverable
kbforge export --kb-root tests/fixtures/sample_kb --format pptx --out cases.pptx
kbforge export --kb-root tests/fixtures/sample_kb --format html --out cases.html
kbforge export --kb-root tests/fixtures/sample_kb --format md   --out cases.md
# --types controls which wiki page types become slides (default: case,pitfall,concept)

# Build a browsable, searchable static site (MkDocs) from the compiled wiki
kbforge site --kb-root tests/fixtures/sample_kb --out site_src
# then: cd site_src && mkdocs serve

# Guard the OKF contract and catch drift after a re-ingest
kbforge validate --kb-root tests/fixtures/sample_kb
kbforge diff    --kb-root tests/fixtures/sample_kb   # baseline snapshot on first run
# Extract claim-level source anchors so RAG can cite the origin post
kbforge enrich  --kb-root tests/fixtures/sample_kb --strategy local
```

### Architecture

One **core** (the single source of truth) wrapped by thin shells:

- **A** — CLI (`kbforge ...`), the `python -m kbforge` entry point.
- **B** — a WorkBuddy Skill (`B-workbuddy-skill/`) that calls core.
- **C** — the importable `kbforge` Python package + `adapters/` for cross-platform.
- **Expert** — a WorkBuddy expert package (`expert/`) reusing core's orchestrator.

See [`docs/design.md`](docs/design.md) for the full design (and [`知识星球整理工具集_开源方案.md`](https://example.invalid) for the planning rationale).

All four forms call the **same core** through the `kbforge` CLI (subprocess), pinned to
`kbforge>=0.1.0,<1.0.0` so a 1.0 API break fails loudly instead of silently breaking B /
the expert (see §12-⑤). The B skill lives in [`B-workbuddy-skill/`](B-workbuddy-skill/SKILL.md);
the expert package in [`expert/`](expert/expert.md).

### Status

**Implemented (tested):** Phase 0 skeleton · exporters (Markdown / PPTX / HTML) ·
delivery forms B (Skill) + Expert · retrieval (`query` / `GraphRetriever` PPR +
BM25, embedding OFF) · publish (`site` MkDocs generator) · **`enrich`** (local
claim anchoring; LLM strategy OFF by default) · **`diff`** (OKF anti-drift guard:
`validate` + snapshot/diff after re-ingest).

**Deferred (not in MVP):** `enrich` LLM strategy (interface implemented, OFF by
default) · `dedupe` cross-post merge · five page types (extend with scheme /
comparison) · MCP server (Phase 4; `query` output is already MCP-friendly). See
[`docs/design.md`](docs/design.md).

### Compliance

This repository contains **only synthetic data** under `tests/fixtures/`. Never commit real posts or attachments — see [`SECURITY.md`](SECURITY.md).

---

## 中文说明

`kb-forge` 是一个**本地优先、默认零外部依赖**的工具集，把社群帖子流整理成干净的知识库，并产出多种格式（含案例 **PPT**）。

- **抓取**：通过可插拔 `PlatformAdapter` 拉取帖子（已内置 Zsxq；可扩展其他平台）。
- **归档**：原始帖按年/月归档，文件名稳定为 `t<topic_id>`。
- **编译 wiki**：概念 / 实体 / 案例 / 踩坑 四类页面，机械层 + 可选 LLM 增强，每条 claim 锚定来源。
- **萃取**：案例/踩坑 → 结构化 `CaseBundle` → 导出 PPT / Markdown / HTML。
- **发布站点**：把 wiki 生成可浏览、可检索的 **MkDocs 静态站**——`[[wiki-link]]` 在生成期即解析为真实链接，用原版 MkDocs 即可构建（零额外依赖）。
- **检索（RAG 就绪）**：`query` 在编译后的 wiki 上做个性化 PageRank（`GraphRetriever`，零 embedding 依赖），可选 embedding 后端（OFF）。
- **产物对齐 OKF**（Google *Open Knowledge Format* v0.1）：Markdown + YAML frontmatter，`type` 必填，链接即知识图谱。

### 安装

```bash
pip install -e ".[dev]"
```

### 快速开始

```bash
python -m kbforge make-fixtures --out tests/fixtures/sample_kb
kbforge build --kb-root tests/fixtures/sample_kb --dry-run
kbforge build --kb-root tests/fixtures/sample_kb
kbforge export --kb-root tests/fixtures/sample_kb --format pptx --out cases.pptx
# RAG-ready retrieval over the compiled wiki (PPR over the link graph)
kbforge query "RAG 评测" --kb-root tests/fixtures/sample_kb --top-k 3
kbforge query "RAG 评测" --kb-root tests/fixtures/sample_kb --format json
# Browsable, searchable static site (stock MkDocs, zero extra deps)
kbforge site --kb-root tests/fixtures/sample_kb --out site_src
# then: cd site_src && mkdocs serve

# 校验 OKF 契约、抓重抓后的漂移
kbforge validate --kb-root tests/fixtures/sample_kb
kbforge diff    --kb-root tests/fixtures/sample_kb   # 首次运行建基线快照
# 抽取 claim 级来源锚点，让 RAG 能回溯原帖
kbforge enrich  --kb-root tests/fixtures/sample_kb --strategy local
```

### 架构

**一个 core（唯一真相源）** + 四层薄封装：A(CLI) / B(WorkBuddy Skill) / C(可 import 框架) / Expert(专家包)。详见 `docs/design.md`。

四层薄封装都通过 `kbforge` CLI（子进程）调用同一个 core，兼容区间钉在
`kbforge>=0.1.0,<1.0.0`（1.0 改 API 会安装即失败告警，见 §12-⑤）。B 在
[`B-workbuddy-skill/`](B-workbuddy-skill/SKILL.md)，专家包在 [`expert/`](expert/expert.md)。

### 当前状态

**已实现（已测试）：** Phase 0 骨架 · 导出族（Markdown / PPTX / HTML）· 交付形态 B（Skill）
+ 专家包 · 检索（`query` / `GraphRetriever` PPR + BM25，embedding OFF）· 发布
（`site` MkDocs 生成器）· **`enrich`**（本地 claim 锚源；LLM 策略默认 OFF）·
**`diff`**（OKF 防漂移守卫：`validate` + 重抓后快照对比）。

**延后（不在 MVP）：** `enrich` 的 LLM 策略（接口已就位，默认 OFF）· `dedupe` 跨帖合并
· 五类页面（扩 scheme / comparison）· MCP server（Phase 4；`query` 输出已对 MCP 友好）。
详见 [`docs/design.md`](docs/design.md)。

### 合规

本仓库 `tests/fixtures/` 仅含**合成数据**。真实帖子/附件**严禁提交**——见 `SECURITY.md`。

---

## License

[Apache-2.0](LICENSE). Methodology inspired by [`obsidian-llm-wiki`](https://github.com/green-dalii/obsidian-llm-wiki) (Apache-2.0); output format aligns with [OKF v0.1](https://github.com/GoogleCloudPlatform/knowledge-catalog) (Apache-2.0). See [`NOTICE`](NOTICE).
