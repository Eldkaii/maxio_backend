# Architecture

Max_io is an amateur football platform: player profiles, balanced matches, bots
that complete teams, results/ELO, player relationships, leagues, a Telegram Mini
App, Telegram bot conversations, and WhatsApp conversations.

```text
Telegram Mini App (/web/) ──┐
Bot Telegram (polling) ─────┼── FastAPI ── SQLAlchemy ── PostgreSQL
Webhook WhatsApp ───────────┘       └── Pillow: PNG cards and photos
```

`start.py` calls `src.main.main()`. It initializes the DB, may start Cloudflare
Tunnel, starts the Telegram bot in a daemon thread, and runs Uvicorn on port
8000.

| Directory | Purpose |
| --- | --- |
| `src/models` | SQLAlchemy tables and relations. |
| `src/schemas` | Pydantic request/response contracts. |
| `src/services` | Business rules. |
| `src/routers` | FastAPI endpoints. |
| `src/bot` | Telegram polling, commands, and conversations. |
| `src/notification` | Notification dispatch and result closure. |
| `src/web` | Static JavaScript/CSS Mini App. |
| `src/utils` | Balancing, seeding, and logging. |

`main.py` registers `/auth/login`, `/maxio/users/*`, `/player/*`,
`/match/matches/*`, `/leagues/*`, `/webhooks/whatsapp`, `/web/`, and `/images/`.
`/` redirects to `/web/`.

The Mini App loads `app.js`, `match-creator.js`, `finalize.js`, `avatar-fix.js`,
and `enhancements.js`. It assumes UI and API share an origin; moving only the UI
to Pages/GitHub Pages requires a configurable API base URL and CORS.

Known modernization work: manual schema migrations live in `database.py`; there
is no Alembic. Some Pydantic v1 `orm_mode` configuration and FastAPI
`@app.on_event("startup")` remain. Several older files have encoding damage;
preserve UTF-8 when editing.

