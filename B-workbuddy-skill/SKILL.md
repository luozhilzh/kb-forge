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
