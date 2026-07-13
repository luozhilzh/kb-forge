# Security Policy

## Intended use

`kb-forge` is a **personal backup / knowledge-engineering tool**. It is designed
to help you organize content *you are already authorized to access* (e.g. posts
from a paid community you belong to).

## Rules of the road

1. **Respect platform Terms of Service.** Do not use `kb-forge` to scrape
   content you are not licensed to retain or redistribute. You are responsible
   for how you use the output.
2. **Never commit real data.** The repository intentionally ships only
   **synthetic** fixtures under `tests/fixtures/`. Real posts, attachments, and
   `group_id` values must stay local and are git-ignored.
3. **No credentials in the repo.**
   - Secrets live in `.env` (git-ignored) or your OS keychain — never in
     `config.yaml` or anywhere committed.
   - Encrypted-attachment passwords are **never persisted**: they are entered
     interactively at runtime (`getpass`) and discarded.
4. **Report a vulnerability** by opening a private security advisory on the
   repository rather than a public issue.

---

## 中文说明

### 预期用途

`kb-forge` 是一个**个人备份 / 知识工程工具**。它用于帮你整理**你本就有权访问**
的内容（例如你所属付费社群的帖子）。

### 使用准则

1. **遵守平台服务条款。** 不要用 `kb-forge` 抓取你无权保留或再分发的內容。
   你对产出的使用方式负责。
2. **绝不提交真实数据。** 本仓库刻意只随附 `tests/fixtures/` 下的**合成**
   fixtures。真实帖子、附件与 `group_id` 必须留在本机，且被 git 忽略。
3. **仓库内不放凭证。**
   - 密钥放在 `.env`（git 忽略）或系统密钥链——绝不能写进 `config.yaml` 或
     任何提交内容。
   - 加密附件的密码**绝不持久化**：运行时由用户交互输入（`getpass`）后即丢弃。
4. **报告漏洞**请在本仓库开私密安全公告（security advisory），不要开公开 issue。
