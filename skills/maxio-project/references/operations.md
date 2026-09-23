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

