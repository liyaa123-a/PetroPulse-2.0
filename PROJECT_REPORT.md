# PetroPulse 2.0 — Project Report (PAT 4)

## 1. Abstract
PetroPulse is a full-stack web application that helps oilfield operators compare planned and actual oil production, quantify shortfalls and their estimated revenue impact, manage wells and targets, and receive transparent rule-based alerts. A React + TypeScript single-page app calls a Flask REST API that validates input, applies business rules and stores all data in an Oracle database; the project also includes Oracle SQL and PL/SQL scripts demonstrating DDL, DML, joins, aggregation, cursors, procedures, functions and triggers.

## 2. Problem statement
Spreadsheets of daily production make it slow to see which wells fall short of plan, by how much, and what that costs. Operators need accurate, consistent metrics, per-user data privacy and an auditable record, not a static demo.

## 3. Objectives
(1) Record wells and daily production per user. (2) Calculate achievement, shortfall, loss %, revenue, profit and revenue loss consistently. (3) Surface under-performance through dashboards, loss analysis and alerts. (4) Keep every user's data isolated and secure. (5) Demonstrate Oracle SQL/PL-SQL competence. (6) Make the system deployable on free-tier cloud services.

## 4. Scope
In: single-oil-product tracking per well per day, targets, alerts, reports, CSV/JSON export. Out: gas tracking, multiple shifts per day, real-time sensor feeds, machine learning, multi-organisation roles, engineering root-cause diagnosis.

## 5. Requirements
**Functional:** authentication; wells CRUD/archive; production CRUD with search, filter, sort, pagination, CSV; dashboard; loss analysis; analytics (day/week/month); targets; alerts; settings; account deletion.
**Non-functional:** security (hashing, token expiry, authorization on every request, parameterised SQL, CORS allow-list); correctness (Decimal arithmetic, one formula module); usability (loading/empty/error states, keyboard focus, responsive); maintainability (modular code, 46 automated tests); deployability (configuration by environment variables).
**Software:** Python 3.11+, Flask, python-oracledb, PyJWT, Gunicorn; Node 18+, React 18, TypeScript, Vite; Oracle Autonomous Database; Git/GitHub; Render; Vercel. **Hardware:** any modern PC with 4 GB RAM and a browser.

## 6. Architecture and data flow
React (Vercel) → HTTPS REST (Render, Gunicorn) → Oracle (TLS/wallet). Flow: user input → client form → API client (bearer token) → server-side validation → Oracle (bind variables, one transaction per request) → business calculations → JSON → charts/tables → insights (alerts, underperforming wells). The browser never connects to Oracle.

## 7. Database design
See `docs/DATABASE_DESIGN.md`: five normalised tables (users, wells, production, targets, alerts) with primary/foreign/unique/check constraints; composite foreign keys `(well_id, user_id)` make cross-user references impossible at the database level. DDL/DML/PL-SQL are in `sql/oracle/01–08` (schema, constraints and indexes, sample data with INSERT/UPDATE/DELETE and COMMIT/ROLLBACK, queries with JOIN/GROUP BY/HAVING/subqueries, procedures, functions, explicit/parameterised cursors, triggers, `run_all.sql`). *These scripts have not been executed against Oracle in the build environment; run them as described in ORACLE_SETUP.md.*

## 8. Business formulas
Shortfall = planned − actual; positive shortfall = max(planned − actual, 0), summed per record; achievement % = actual ÷ planned × 100; loss % = positive shortfall ÷ planned × 100; revenue = actual × price; operating profit = revenue − cost; revenue loss = positive shortfall × price. Units: barrels, USD. Zero planned production yields "not defined" rather than an error. Example: planned 1000, actual 800, price $70, cost $1000 → 80 %, 200 bbl, 20 %, $56,000, $55,000, $14,000.

## 9. API design
Resource-oriented JSON API with uniform success/error envelopes, correct status codes, pagination, filtering, and no internal details in errors. Full list: `docs/API_REFERENCE.md`.

## 10. UI/UX
Light enterprise theme (warm off-white, navy text, teal/blue accents; green/amber/red for performance), persistent sidebar, breadcrumb top bar, alert bell, user menu, KPI cards, SVG charts with units and tooltips, accessible dialogs, confirmation for destructive actions, loading/empty/error states, responsive and print-friendly layouts, dark-mode aware. Screenshots: `docs/screenshots/`.

## 11. Security
scrypt password hashing; 60-minute bearer tokens with server-side revocation (`token_version`); ownership checks in every SQL statement plus composite foreign keys; other users' ids return 404; validation of all inputs; bind variables only; CORS exact-origin allow-list without credentials; login/registration rate limiting; CSV formula-injection neutralised; secrets only in environment variables or Render secret files; wallet never in Git or the ZIP; startup refuses unsafe production configuration; no SQLite path in production. Limitations: in-memory rate limiter is per process; tokens in `sessionStorage` are exposed to XSS (mitigated by short life and no raw HTML rendering).

## 12. Installation, execution, Oracle setup, deployment
See `README.md`, `ORACLE_SETUP.md`, `DEPLOYMENT_GUIDE.md`.

## 13. Testing approach and actual results
See `docs/TESTING.md`. Observed: 46 backend tests passed (1 live-Oracle test skipped by design); TypeScript check and production build passed; Chromium run of the real UI against the real API on the SQLite test harness succeeded; Gunicorn started and reported database `unavailable` correctly without Oracle. Not verified: real Oracle, Render, Vercel.

## 14. Sample input/output
Input `POST /api/production {"well_id":1,"production_date":"2026-10-15","planned_oil":1000,"actual_oil":800,"oil_price":70,"operating_cost":1000}` → output achievement 80.0, shortfall 200.0, revenue 56000.0, operating profit 55000.0, revenue loss 14000.0. A repeat for the same well and date → 409 `DUPLICATE_RECORD`.

## 15. Limitations
Alerts are evaluated on save/on demand (no scheduler); aggregates are computed in Python from the user's filtered rows (fine for thousands of records, not millions); revenue loss uses the recorded price (an estimate); single time zone (dates only); free-tier hosting sleeps and has quotas.

## 16. Future improvements
Gas and multi-product support, scheduled alert jobs, refresh tokens with httpOnly cookies, SQL-side aggregation views, role-based multi-user organisations, CSV import, forecasting (only if a real, tested model is added).
