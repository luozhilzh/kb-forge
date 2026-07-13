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
