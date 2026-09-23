# Safe operation, tests, and migrations

PostgreSQL is required. `init_db()` in `database.py` creates tables and performs
manual, idempotent compatibility migrations. There is no migration framework.
Do not add destructive SQL or assume schema state without reviewing existing
installations and obtaining authorization.

## Critical test safety condition

`src/test/conftest.py` executes `Base.metadata.drop_all()` at session setup and
teardown, and before every test. It uses `settings.DATABASE_URL`, so pytest can
erase the development database. This has already happened in local development.

Before running tests, create a dedicated DB such as `maxiodb_test`, force that
URL before importing `src.database`, and add a guard that rejects `drop_all()`
unless the URL is unmistakably a test database. Until then, never run the test
launchers. `python -m compileall -q src` is the safe syntax check.

For normal work: check Git status, preserve unrelated changes, trace router →
service → model/schema → frontend or integration, and run `git diff --check`
before delivery. Do not reset or clean the working tree without an explicit
request.

## Executable release review

`releaser.py` packages a Windows executable using PyInstaller. Every commit
requires a release review before it is created:

1. Decide whether it changes a distributed feature, dependency, bundled static
   resource, executable entrypoint or release configuration.
2. If it does, update `releaser.py` and advance `VERSION` according to the
   project's release convention. If it does not, retain the version and state
   that decision in `manuales/commits/<fecha>-<tema>.md`.
3. For an actual release build, confirm that the bundle contains `web/`,
   `images/`, `fonts/` and, for `APP_ENV=TEST`, `tools/cloudflared.exe`.
4. Do not distribute a copied real `.env`. The current script copies it into
   `dist/` for local use; replace that behavior with a template or explicit
   configuration step before sharing a release outside the controlled
   environment.

The generated `.spec` files are build artifacts; `releaser.py` regenerates the
current one. Do not manually treat an old `.spec` as the authoritative bundle
definition.

## End-of-session time record

For every session with material Max_io work, before the final response register
the time in the sibling project management repository at
`../la_gerencia/datos.json` (normally `C:\\Proyectos\\la_gerencia\\datos.json`).
This project requirement is standing authorization to perform that scoped
recording; comply with any execution-time permission prompt required to write
outside this repository.

1. Read the JSON and find exactly one project whose `name` is `Max_io`; do not
   create a second project entry.
2. Add one `time_entries` object with numeric `hours`, ISO date (`YYYY-MM-DD`),
   and a concise factual `description` of the session's material work. Use the
   actual elapsed working time, reasonably rounded; do not invent time when it
   cannot be established.
3. Before writing, check that an entry for the same date, duration, and session
   description was not already added. Preserve every other field and entry.
4. Make a dated backup or use the manager's atomic-save pattern, then reread
   the file to verify the entry and the resulting Max_io total.

If the sibling repository or its data file is unavailable, state that plainly in
the final response; do not silently omit the required record.
