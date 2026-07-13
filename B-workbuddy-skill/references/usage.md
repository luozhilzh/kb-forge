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
