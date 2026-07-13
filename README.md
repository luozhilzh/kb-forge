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
```

### Architecture

One **core** (the single source of truth) wrapped by thin shells:

- **A** — CLI (`kbforge ...`), the `python -m kbforge` entry point.
- **B** — a WorkBuddy Skill (`B-workbuddy-skill/`) that calls core.
- **C** — the importable `kbforge` Python package + `adapters/` for cross-platform.
- **Expert** — a WorkBuddy expert package (`expert/`) reusing core's orchestrator.

See [`docs/design.md`](docs/design.md) for the full design (and [`知识星球整理工具集_开源方案.md`](https://example.invalid) for the planning rationale).

### Compliance

This repository contains **only synthetic data** under `tests/fixtures/`. Never commit real posts or attachments — see [`SECURITY.md`](SECURITY.md).

---

## 中文说明

`kb-forge` 是一个**本地优先、默认零外部依赖**的工具集，把社群帖子流整理成干净的知识库，并产出多种格式（含案例 **PPT**）。

- **抓取**：通过可插拔 `PlatformAdapter` 拉取帖子（已内置 Zsxq；可扩展其他平台）。
- **归档**：原始帖按年/月归档，文件名稳定为 `t<topic_id>`。
- **编译 wiki**：概念 / 实体 / 案例 / 踩坑 四类页面，机械层 + 可选 LLM 增强，每条 claim 锚定来源。
- **萃取**：案例/踩坑 → 结构化 `CaseBundle` → 导出 PPT / Markdown / HTML。
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
```

### 架构

**一个 core（唯一真相源）** + 四层薄封装：A(CLI) / B(WorkBuddy Skill) / C(可 import 框架) / Expert(专家包)。详见 `docs/design.md`。

### 合规

本仓库 `tests/fixtures/` 仅含**合成数据**。真实帖子/附件**严禁提交**——见 `SECURITY.md`。

---

## License

[Apache-2.0](LICENSE). Methodology inspired by [`obsidian-llm-wiki`](https://github.com/green-dalii/obsidian-llm-wiki) (Apache-2.0); output format aligns with [OKF v0.1](https://github.com/GoogleCloudPlatform/knowledge-catalog) (Apache-2.0). See [`NOTICE`](NOTICE).
