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
- **Code comments in English; docs are bilingual** (English first, then a
  `## 中文说明` section — avoids mojibake in others' editors while staying
  readable for Chinese contributors).
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
3. Add it to `adapters/__init__.py` and document it in `docs/design.md`.
   See `adapters/example_wechat.py` for a skeleton.

## Commit style

Conventional commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`) are
appreciated but not enforced.

---

## 中文说明

感谢你对 `kb-forge` 的关注！

### 开发环境

```bash
pip install -e ".[dev]"
pre-commit install   # ruff + black + mypy
```

### 约定

- **一个核心，薄封装。** 所有真实逻辑都在 `src/kbforge/core/`。CLI（A）、
  Skill（B）、可 import 框架（C）、专家包都是薄封装。
- **代码注释用英文；文档用双语**（英文在前，后接 `## 中文说明` 段——既避免他人
  编辑器乱码，又照顾中文贡献者阅读）。
- **测试互相隔离（hermetic）。** 纯逻辑 + mock adapter 测试处处可跑（含 Windows CI
  矩阵）。需要网络 / 真实凭证的测试打 `@pytest.mark.e2e` 标签，从 Windows 矩阵排除。
- **fixtures 均为合成数据**，提交在 `tests/fixtures/`。用
  `python -m kbforge make-fixtures` 重新生成。

### 运行测试

```bash
pytest                     # 除 e2e 外全部
pytest -m "not e2e"        # 显式（即 CI 的 Windows 矩阵所跑）
pytest -m e2e              # 需网络 / 真实凭证（仅本地）
```

### 新增平台适配器

1. 继承 `kbforge.adapters.base.PlatformAdapter`。
2. 实现 `fetch_topics` / `download_attachment` / `paginate`。
3. 注册进 `adapters/__init__.py`，并在 `docs/design.md` 中补文档。
   参考 `adapters/example_wechat.py` 骨架。

### 提交风格

推荐 Conventional Commits（`feat:` / `fix:` / `docs:` / `test:` / `chore:`），
但不强制。
