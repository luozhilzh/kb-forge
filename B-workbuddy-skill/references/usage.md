# kb-forge usage (HOWTO)

The single source of truth for operating `kbforge`. Loaded by both the B skill
and the expert package.

## 1. Install

```bash
pip install "kbforge>=0.1.0,<1.0.0"   # upper bound guards against 1.0 API break
# or, from a checkout:
pip install -e ".[dev]"
```

Verify: `python -m kbforge --help`.

## 2. Configure

`config.yaml` (non-secret, git-ignored). Copy from `config.example.yaml`:

| key | meaning |
|---|---|
| `kb_root` | knowledge-base root (absolute or relative to config file) |
| `group_id` | platform group id (placeholder `planet_demo_001` for the demo) |
| `platform` | adapter name, e.g. `zsxq` |
| `local_attach_dir` | where raw attachments are staged |
| `zsxq_cli_path` | path/command to the zsxq CLI (default `zsxq-cli`) |
| `output.formats` | default export formats, e.g. `[pptx, md]` |
| `wiki.schema_path` | `SCHEMA.md` topic list |
| `wiki.enrich.enabled` | LLM enhancement — **off by default** |
| `fetch.incremental` | resume from cursor (off in MVP) |
| `paths.*` | `raw` / `wiki` / `archive` / `cases` / `attachments` subdirs |
| `query.backend` | `graph` (PPR, zero-dep) | `embedding` (optional, OFF) |

Secrets in `.env` next to the config (never committed):
```
ZSXQ_TOKEN=...
LLM_API_KEY=...
```

## 3. Commands

| command | purpose |
|---|---|
| `make-fixtures --out <dir>` | generate a synthetic demo KB (no real data) |
| `build --kb-root <dir> [--dry-run] [--stage ...] [--topic t123] [--profile ...]` | compile the OKF wiki |
| `export --kb-root <dir> --format pptx\|html\|md [--out <file>] [--types case,pitfall,concept]` | extract `CaseBundle`s and render |
| `query "<text>" [--top-k N] [--backend graph\|embedding] [--format text\|json]` | RAG-ready retrieval (PPR over the link graph) |
| `site --kb-root <dir> [--out DIR] [--theme material\|readthedocs\|mkdocs] [--build/--no-build]` | browsable MkDocs site |
| `validate --kb-root <dir>` | OKF contract check (type / hash / broken links) |
| `diff --kb-root <dir>` | anti-drift guard; baseline snapshot on first run |
| `enrich --kb-root <dir> [--strategy local\|none]` | claim-level source anchors for RAG citing |
| `mcp [--transport stdio\|sse]` | expose all of the above as standard MCP tools (requires `pip install 'kbforge[mcp]'`) |

## 4. Compliance (non-negotiable)

- This repo contains **only synthetic data** under `tests/fixtures/`. Real
  posts / attachments must never enter the open-source tree.
- `.env` is git-ignored. Encrypted-attachment passwords are typed at runtime
  and never written to disk.
- Every wiki claim anchors to `source:`; exports preserve that traceability.

## 5. Platform notes (learned the hard way)

- **Windows**: run `kbforge` from **Git Bash** or PowerShell, not `cmd.exe`.
  The toolkit ships **no `.bat` files** (GBK encoding traps); use the `python -m
  kbforge` entry point.
- **zsxq-cli on Windows**: if you hit a `WinError 193` (it is a POSIX shell
  script, not an `.exe`), invoke it through Git Bash, not `subprocess` directly.
- **No network for e2e**: pure-logic tests run on the CI dual matrix (Ubuntu +
  Windows); only `@pytest.mark.e2e` needs real credentials.

---

## 中文说明

`kbforge` 操作的权威 HOWTO，B Skill 与专家包共用同一份。

### 1. 安装

```bash
pip install "kbforge>=0.1.0,<1.0.0"   # 上界防止 1.0 改 API 静默破坏
# 或从源码安装：
pip install -e ".[dev]"
```

验证：`python -m kbforge --help`。

### 2. 配置

`config.yaml`（非秘密，git 忽略）。从 `config.example.yaml` 复制：

| 键 | 含义 |
|---|---|
| `kb_root` | 知识库根目录（相对 config 文件或绝对路径） |
| `group_id` | 平台群组 id（演示可用占位 `planet_demo_001`） |
| `platform` | adapter 名称，如 `zsxq` |
| `local_attach_dir` | 原始附件暂存目录 |
| `zsxq_cli_path` | zsxq CLI 路径/命令（默认 `zsxq-cli`） |
| `output.formats` | 默认导出格式，如 `[pptx, md]` |
| `wiki.schema_path` | `SCHEMA.md` 主题清单 |
| `wiki.enrich.enabled` | LLM 增强——**默认关闭** |
| `fetch.incremental` | 从游标续跑（MVP 关闭） |
| `paths.*` | `raw` / `wiki` / `archive` / `cases` / `attachments` 子目录 |
| `query.backend` | `graph`（PPR，零依赖）\| `embedding`（可选，OFF） |

密钥放 config 同目录的 `.env`（绝不提交）：
```
ZSXQ_TOKEN=...
LLM_API_KEY=...
```

### 3. 命令

| 命令 | 用途 |
|---|---|
| `make-fixtures --out <dir>` | 生成合成演示知识库（无真实数据） |
| `build --kb-root <dir> [--dry-run] [--stage ...] [--topic t123] [--profile ...]` | 编译 OKF wiki |
| `export --kb-root <dir> --format pptx\|html\|md [--out <file>] [--types case,pitfall,concept]` | 萃取 `CaseBundle` 并渲染 |
| `query "<文本>" [--top-k N] [--backend graph\|embedding] [--format text\|json]` | RAG 就绪检索 |
| `site --kb-root <dir> [--out DIR] [--theme material\|readthedocs\|mkdocs] [--build/--no-build]` | 生成可浏览 MkDocs 站点 |
| `validate --kb-root <dir>` | OKF 契约校验（type / hash / 断链） |
| `diff --kb-root <dir>` | 防漂移守卫；首次运行建基线快照 |
| `enrich --kb-root <dir> [--strategy local\|none]` | 抽取 claim 级来源锚点，供 RAG 回溯 |
| `mcp [--transport stdio\|sse]` | 把上述全部能力暴露成标准 MCP 工具（需 `pip install 'kbforge[mcp]'`） |

### 4. 合规（不可妥协）

- 本仓库 `tests/fixtures/` 下**仅含合成数据**。真实帖子 / 附件绝不进入开源树。
- `.env` 被 git 忽略。加密附件密码运行时键入，绝不落盘。
- 每条 wiki claim 都锚定 `source:`；导出保留该可追溯性。

### 5. 平台注意事项（踩坑所得）

- **Windows**：用 **Git Bash** 或 PowerShell 跑 `kbforge`，别用 `cmd.exe`。
  工具集**不随附任何 .bat 文件**（GBK 编码陷阱）；统一用 `python -m kbforge` 入口。
- **Windows 上的 zsxq-cli**：若遇 `WinError 193`（它是 POSIX shell 脚本而非
  `.exe`），经 Git Bash 调用，别直接走 `subprocess`。
- **e2e 无网络**：纯逻辑测试跑在 CI 双矩阵（Ubuntu + Windows）；只有
  `@pytest.mark.e2e` 需要真实凭证。
