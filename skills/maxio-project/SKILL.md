---
name: maxio-project
description: Work safely on the Max_io football platform. Use for any code, bug-fix, feature, test, configuration, or integration task inside this repository.
metadata:
  short-description: Max_io project context and safeguards
---

# Max_io project skill

This is a repository-local skill. It is intentionally stored with the source so
any AI working on a clone can read the same project context. Read
`../../AGENTS.md` first; it provides the broad technical overview.

## Mandatory directives

1. Run `git status --short` before editing. Preserve all pre-existing changes.
2. Never print, commit, copy, or expose values from `.env`, credentials, tokens,
   passwords, or private user data.
3. Do **not** run `pytest`, `start_test.py`, or `src/run_test.py` with the
   ordinary `.env`. The present pytest fixture calls `drop_all()` on the
   configured database and can delete every table.
4. Do not reset, recreate, seed, migrate destructively, or alter a real database
   without explicit user authorization and a verified recovery path.
5. PostgreSQL is mandatory. Do not substitute SQLite for integration work:
   player history relies on PostgreSQL `ARRAY`.
6. Keep business rules in `src/services`; keep routers thin. Require identity and
   appropriate permissions for every new mutable endpoint.
7. Preserve UTF-8 text, avoid destructive Git commands, and inspect `git diff
   --check` before delivery.

## Read by task, not all at once

| Task | Read |
| --- | --- |
| Startup, folders, endpoint prefixes, Mini App | [architecture.md](references/architecture.md) |
| Models, matches, bots, results, leagues, rankings | [domain.md](references/domain.md) |
| `.env`, Telegram, WhatsApp, Cloudflare Tunnel | [integrations.md](references/integrations.md) |
| Tests, migrations, data safety, verification | [operations.md](references/operations.md) |

For cross-cutting work, read the relevant combination before changing code.
User instructions take precedence except for the data-safety restrictions above.

