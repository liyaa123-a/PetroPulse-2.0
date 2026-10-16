# Testing

## Run
```powershell
cd backend ; .\.venv\Scripts\Activate.ps1 ; pip install -r requirements-dev.txt
python -m pytest -q                       # 46 tests, no Oracle needed
$env:RUN_ORACLE_TESTS="1" ; python -m pytest tests\test_oracle_live.py -v     # live Oracle (needs ORACLE_* set)
python scripts\check_oracle.py            # connectivity + schema check
cd ..\frontend ; npm install ; npm run build    # type-check + production build
```
## Strategy
Business rules live in pure functions (`calculations.py`) tested without any database. API behaviour (auth, authorization, validation, filters, CSV, analytics, alerts, targets, deletion, error handling) is tested through Flask's test client on an **in-memory SQLite database that mirrors the Oracle schema** (`tests/sqlite_schema.sql`). SQLite is used **only** there and in `scripts/preview_sqlite.py`; production code has no SQLite path. Because SQLite is not Oracle, `tests/test_oracle_live.py` re-runs the main flow (register → well → record → duplicate rejected by the Oracle unique constraint → dashboard maths → OFFSET/FETCH paging → CSV → account deletion) against a real Oracle database once you configure one. The SQL layer rejects unused/missing bind variables on every backend so bind errors surface in unit tests.

## What the 46 tests cover
Formulas incl. zero planned, overproduction, negative/NaN input, decimal precision · registration, login, no user enumeration, hashing, duplicate email, rate limit, logout/password-change token revocation, 401 on every protected route · well CRUD, duplicate codes per user, archive keeps history, search with escaped wildcards · record validation, duplicates, update/delete, archived well, filters/sort/pagination/CSV (formula-injection safe) · **cross-user isolation** on wells, records, targets, alerts, dashboard, exports, plus DB-level foreign-key rejection · dashboard/loss/summary values checked against hand calculations · target statuses and overlap rule · all four alert rules, de-duplication, thresholds, workflow · export + account deletion removing only the caller's data · CORS allow-list, unsafe-config refusal, database-down handling without leaking internals, demo seed/removal.

## Results observed when this package was built
- Backend: `46 passed, 1 skipped` (the skipped test is the live-Oracle test).
- Frontend: `tsc --noEmit` clean; `vite build` succeeded; the built bundle contains no `localhost` URL.
- Browser run (Chromium via Playwright; real React app → real Flask API → SQLite test harness with demo data): wrong password rejected; dashboard, wells, records, loss, analytics, targets, alerts, settings all rendered with data; a reload on a nested route kept the session; a far-future date was rejected with a field error; a second account saw no data of the first. Screenshots in `docs/screenshots/` were captured from that run.
- Gunicorn started `wsgi:app` with production-style settings and no Oracle configured; `/api/health/live` returned 200 and `/api/health` returned 503 `database: unavailable`.

## NOT verified (needs your accounts)
Real Oracle connection and the SQL/PL-SQL scripts executing (they were written carefully but never run against Oracle), the Render deployment, the Vercel deployment, CORS between the real deployed URLs, wallet handling on Render. Use `check_oracle.py`, `test_oracle_live.py` and the checklist in `DEPLOYMENT_GUIDE.md`.

## Capturing your own screenshots
Run the stack as in the README (with Oracle + `python -m app.seed`), sign in as the demo user, and save screenshots of each page into `docs/screenshots/`.
