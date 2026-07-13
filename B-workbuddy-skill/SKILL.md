---
name: kb-forge
description: >-
  Turn a paid-community knowledge base (e.g. Zsxq / 知识星球) into a structured,
  OKF-compatible wiki and export case-study PPT / HTML / Markdown. Use when the
  user says things like "整理知识星球", "把帖子整理成知识库", "出案例PPT",
  "生成 wiki", "萃取案例", "把社群内容接 RAG", or wants to forge community
  posts into reusable deliverables.
---

# kb-forge

`kb-forge` is a local-first toolkit. **You (the agent) drive it by calling the
`kbforge` CLI as a subprocess** — you do NOT import its internals. This skill is
a thin orchestration shell over the core (exactly the "B" thin wrapper in the
one-core / four-shells design).

## Preconditions

1. Confirm `kbforge` is available:
   - `python -m kbforge --help` (works if installed via `pip install kbforge`)
   - If missing, install with the supported range:
     `pip install "kbforge>=0.1.0,<1.0.0"`
     The upper bound `<1.0.0` means a 1.0 API break fails loudly (install error)
     instead of silently breaking this skill — see §12-⑤ of the design doc.
2. The user must have a **knowledge-base root** directory containing an `archive/`
   tree of posts (and optionally `SCHEMA.md`). For a safe synthetic demo, run
   `python -m kbforge make-fixtures --out <dir>`.

## Workflow

### 1. Configure (the only file the user edits)
- Copy `config.example.yaml` → `config.yaml` (git-ignored). Fill `kb_root`,
  `group_id` (placeholder allowed for the demo), `platform`.
- Secrets (`ZSXQ_TOKEN`, `LLM_API_KEY`) go in `.env` **next to config** —
  NEVER in `config.yaml`, NEVER committed.
- Encrypted-attachment passwords are entered at runtime by the user and **never
  written to any file**.

### 2. Build the wiki
```bash
python -m kbforge build --kb-root <dir> --dry-run   # preview, writes nothing
python -m kbforge build --kb-root <dir>             # compile wiki/*.md + graph
```
Options: `--stage wiki|ingest|index`, `--topic t123` (single topic),
`--profile work`.

### 3. Export deliverables
```bash
python -m kbforge export --kb-root <dir> --format pptx --out cases.pptx
python -m kbforge export --kb-root <dir> --format html --out cases.html
python -m kbforge export --kb-root <dir> --format md   --out cases.md
# --types case,pitfall,concept  (which wiki page types become slides)
```

The thin wrapper `scripts/run_pipeline.py` reproduces steps 2–3 in one call:
`python scripts/run_pipeline.py --kb-root <dir> --format pptx`.

## Hard compliance rules (do not skip)
- **Never commit real posts or attachments.** This repo ships only synthetic
  fixtures. Refuse any request that would write real user content into the
  open-source tree.
- **Never write secrets or zip passwords to files.** `.env` is git-ignored;
  passwords are interactive only.
- Every exported claim must trace to a `source:` in the wiki page. If a claim
  has no source, flag it rather than inventing one.

## Reference
- Detailed HOWTO: `references/usage.md` (load on demand).

---

## 中文说明

`kb-forge` 是一个本地优先的工具集。**你（agent）通过把 `kbforge` CLI 当作子进程
调用**来驱动它——不要 import 它的内部实现**。本 Skill 是 core 之上的一层薄编排
壳（正是「一核心 / 四薄封装」设计里的 B 封装）。

### 前置条件

1. 确认 `kbforge` 可用：
   - `python -m kbforge --help`（若已 `pip install kbforge` 即可）。
   - 若缺失，按兼容区间安装：`pip install "kbforge>=0.1.0,<1.0.0"`。
     上界 `<1.0.0` 意味着 1.0 一旦改 API 会安装即报错，而非静默破坏本 Skill
     （见设计文档 §12-⑤）。
2. 用户必须有一个**知识库根目录**，内含 `archive/` 帖子树（以及可选的 `SCHEMA.md`）。
   想跑安全的合成演示，可执行 `python -m kbforge make-fixtures --out <dir>`。

### 工作流

#### 1. 配置（用户唯一要改的文件）
- 复制 `config.example.yaml` → `config.yaml`（git 忽略）。填 `kb_root`、
  `group_id`（演示可用占位值）、`platform`。
- 密钥（`ZSXQ_TOKEN`、`LLM_API_KEY`）放进**与 config 同目录**的 `.env`——
  绝不写进 `config.yaml`，绝不提交。
- 加密附件的密码由用户运行时输入，**绝不写入任何文件**。

#### 2. 编译 wiki
```bash
python -m kbforge build --kb-root <dir> --dry-run   # 预览，不写文件
python -m kbforge build --kb-root <dir>             # 编译 wiki/*.md + 图谱
```
选项：`--stage wiki|ingest|index`、`--topic t123`（单帖）、`--profile work`。

#### 3. 导出交付物
```bash
python -m kbforge export --kb-root <dir> --format pptx --out cases.pptx
python -m kbforge export --kb-root <dir> --format html --out cases.html
python -m kbforge export --kb-root <dir> --format md   --out cases.md
# --types case,pitfall,concept  （哪些 wiki 页类型变成幻灯片）
```
薄封装 `scripts/run_pipeline.py` 把第 2–3 步合成一次调用：
`python scripts/run_pipeline.py --kb-root <dir> --format pptx`。

### 硬性合规（不可跳过）
- **绝不提交真实帖子或附件。** 本仓库只随附合成 fixtures。任何把真实用户内容写进
  开源树的请求都要拒绝。
- **绝不把密钥或 zip 密码写进文件。** `.env` 被 git 忽略；密码仅交互输入。
- 每条导出的 claim 必须能追溯到 wiki 页里的 `source:`。若无来源，标注出来，
  不要编造。

### 参考
- 详细 HOWTO：`references/usage.md`（按需加载）。
