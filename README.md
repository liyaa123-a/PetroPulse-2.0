# PetroPulse 2.0 — Oilfield Production & Loss Intelligence System



```
 React + TypeScript (Vercel)  ──HTTPS──►  Flask REST API (Render)  ──oracledb, TLS/wallet──►  Oracle Autonomous Database
        frontend/                              backend/                                        sql/oracle/
```

The browser never talks to Oracle and never sees credentials. All validation, authorization and calculations run on the server.

## What is implemented
Registration/login/logout, password change, account deletion · executive dashboard · wells (add, edit, status, archive, detail + history) · production records (CRUD, search, filter, sort, pagination, CSV) · loss analysis · analytics (day/week/month, well comparison, CSV, print) · production targets (overlap rule, MET/AT_RISK/MISSED) · rule-based alerts (acknowledge/resolve) · settings (thresholds, units, JSON export) · Oracle DDL/DML/PL-SQL scripts · automated tests.

## Folder map
| Path | Purpose |
|---|---|
| `frontend/` | React + TS + Vite app (deploy to Vercel). `vercel.json` handles SPA routing. |
| `backend/` | Flask API (`app/`), `wsgi.py`, `gunicorn.conf.py`, tests, helper scripts (deploy to Render) |
| `sql/oracle/` | `01`–`08` scripts + `run_all.sql` (DDL, constraints, DML, queries, procedures, functions, cursors, triggers) |
| `render.yaml` | Render blueprint (secrets are entered in the dashboard) |
| `docs/` | API reference, database design, testing, screenshots |
| `ORACLE_SETUP.md` · `DEPLOYMENT_GUIDE.md` · `PROJECT_REPORT.md` | Step-by-step guides and the academic report |

## Quick start on Windows (PowerShell)
Prerequisites: Python 3.11+, Node 18+, Git, VS Code, and an Oracle schema created with [ORACLE_SETUP.md](ORACLE_SETUP.md).
```powershell
Expand-Archive PetroPulse_2.0_Final.zip -DestinationPath C:\Projects ; cd C:\Projects\PetroPulse_2.0 ; code .

# Backend
cd backend
python -m venv .venv ; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
copy ..\.env.example .env          # then edit backend\.env: APP_ENV=development, SECRET_KEY, FRONTEND_ORIGIN=http://localhost:5173, ORACLE_*
python scripts\check_oracle.py     # verifies connection + tables
python -m pytest -q                # unit tests (no Oracle needed)
$env:DEMO_PASSWORD="ChooseADemoPassword1" ; python -m app.seed   # optional demo data
flask --app wsgi run --port 5000   # API at http://localhost:5000

# Frontend (second terminal)
cd C:\Projects\PetroPulse_2.0\frontend
npm install
npm run dev                        # http://localhost:5173  (uses VITE_API_BASE_URL from .env.development)
npm run build                      # production build -> dist/
```
Open <http://localhost:5173>, register, add a well, add a production record.
`gunicorn` does not run on Windows; locally use `flask run`. Production (Render) uses Gunicorn.

## Authentication design
Short-lived (60 min) signed **bearer tokens** (HS256 JWT) in the `Authorization` header. Passwords are hashed with salted **scrypt**. Each token carries the user's `token_version`; logout, password change and account deletion invalidate all earlier tokens server-side. No cookies → no CSRF, and CORS needs no credentials. *Trade-off:* the SPA keeps the token in `sessionStorage` (cleared when the tab closes) so a refresh doesn't log you out; an XSS bug could read it, so the app renders no raw HTML and tokens expire quickly. In-memory-only storage would be safer but logs the user out on every refresh.

## Business formulas (units: barrels, USD)
`Shortfall = planned − actual` · `Positive shortfall = max(planned − actual, 0)` (summed per record) · `Achievement % = actual ÷ planned × 100` · `Loss % = positive shortfall ÷ planned × 100` · `Revenue = actual × price` · `Operating profit = revenue − cost` · `Revenue loss = positive shortfall × price` (an estimate, not accounting). Zero planned production returns "no value" instead of dividing by zero. Implemented once in `backend/app/calculations.py`; the dashboard, loss analysis, analytics, exports and Oracle functions use the same definitions.

## Honest status
See [docs/TESTING.md](docs/TESTING.md) for exactly what was and was not verified. In short: unit/API tests, the frontend build and a browser run were executed against a **test-only SQLite harness**; **no real Oracle database, Render or Vercel deployment was available when this was built**, so those steps are yours to perform with the guides.
