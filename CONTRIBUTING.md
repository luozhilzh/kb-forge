# Contributing

Thanks for your interest in `kb-forge`!

## Dev setup

```bash
pip install -e ".[dev]"
pre-commit install   # ruff + black + mypy
```

## Conventions

- **One core, thin shells.** All real logic lives in `src/kbforge/core/`. The
  CLI (A), Skill (B), framework (C), and expert package are thin wrappers.
- **Code comments in English; docs in Chinese** (avoids mojibake in others'
  editors).
- **Tests are hermetic.** Pure-logic + mock-adapter tests run everywhere
  (including the Windows CI matrix). Network / real-credential tests are tagged
  `@pytest.mark.e2e` and excluded from Windows.
- **Fixtures are synthetic** and checked in under `tests/fixtures/`. Regenerate
  with `python -m kbforge make-fixtures`.

## Running tests

```bash
pytest                     # everything except e2e
pytest -m "not e2e"        # explicit (what CI's Windows matrix runs)
pytest -m e2e              # needs network / real credentials (local only)
```

## Adding a platform adapter

1. Subclass `kbforge.adapters.base.PlatformAdapter`.
2. Implement `fetch_topics` / `download_attachment` / `paginate`.
3. Add it to `adapters/__init__.py` and document it in `docs/guide.md`.
   See `adapters/example_wechat.py` for a skeleton.

## Commit style

Conventional commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`) are
appreciated but not enforced.
