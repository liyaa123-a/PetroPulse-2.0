# Oracle Autonomous Database setup (beginner guide)

Goal: a free Oracle Autonomous Database, a dedicated **application user** (never ADMIN), the PetroPulse tables, and the connection details for the backend. Oracle's menus change occasionally; names below match the console at the time of writing. Free-tier eligibility and limits depend on your account and region — check Oracle's current "Always Free" page. A credit card is normally required to verify a new Oracle Cloud account.

## 1. Create the database
1. Sign up / sign in at <https://cloud.oracle.com>.
2. Open the menu (☰) → **Oracle Database** → **Autonomous Database** → **Create Autonomous Database**.
3. Display name `PetroPulse`, database name `PETROPULSE`. Workload type **Transaction Processing**, deployment **Serverless**.
4. Turn on the **Always Free** toggle. If it is greyed out or unavailable in your region, you cannot get a free instance there: choose another home region you are eligible for, or use a paid/trial instance — do **not** switch the app to SQLite.
5. Set the **ADMIN password** yourself and store it privately (never in chat or Git).
6. **Network access:** choose **Secure access from everywhere** and keep **Require mutual TLS (mTLS) authentication** enabled. With mTLS the wallet is the credential, so Render's changing IP addresses are not a problem. (If you instead restrict access to an IP allow-list, you must allow Render's outbound IPs — your laptop IP alone will not work for the deployed API.)
7. Click **Create** and wait until the state is **Available**.

## 2. Create the application user
Database details page → **Database actions** → **SQL** (signed in as ADMIN). Run (choose your own strong password, no `@` or quotes):
```sql
CREATE USER petropulse_app IDENTIFIED BY "ChooseAStrongPassw0rd#";
ALTER USER petropulse_app QUOTA UNLIMITED ON DATA;
GRANT CREATE SESSION, CREATE TABLE, CREATE VIEW, CREATE SEQUENCE, CREATE PROCEDURE, CREATE TRIGGER TO petropulse_app;
```
Only these privileges are granted. Then enable SQL web access for that user: Database actions → **Database Users** → `PETROPULSE_APP` → switch on **Web access** → copy its URL and sign in as `petropulse_app`.

## 3. Create the schema
In the SQL worksheet signed in as `petropulse_app`, paste each file from `sql/oracle/` and click **Run Script** (F5), in this order:
`01_schema.sql` → `02_constraints_indexes.sql` → `06_functions.sql` → `05_procedures.sql` → `08_triggers.sql` → `03_sample_data.sql` (optional) → `04_queries.sql` → `07_cursors.sql`.
(`run_all.sql` does the same in one go from SQLcl/SQL*Plus using `@` includes.) Re-running `01_schema.sql` is safe: it fails with ORA-00955 instead of overwriting data.
Verify: `SELECT table_name FROM user_tables;` must list `PP_USERS, PP_WELLS, PP_PRODUCTION, PP_TARGETS, PP_ALERTS`. Check objects with `SELECT object_name, status FROM user_objects WHERE status <> 'VALID';` (should return no rows).

## 4. Download the wallet and note the connection values
Database details → **Database connection** → **Download wallet** → *Instance wallet* → set a **wallet password** (this is `ORACLE_WALLET_PASSWORD`) → download the zip. Keep it private; never commit it. Unzip it **outside the repository** (e.g. `C:\petropulse\wallet`). You need two files from it: `tnsnames.ora` and `ewallet.pem`.
Open `tnsnames.ora`: it lists service aliases such as `petropulse_low`, `petropulse_tp`, `petropulse_high`. Use `petropulse_low` or `petropulse_tp` as `ORACLE_DSN` (HIGH uses more of the free instance's concurrency).

| Variable | Value |
|---|---|
| `ORACLE_USER` | `PETROPULSE_APP` |
| `ORACLE_PASSWORD` | the app-user password from step 2 |
| `ORACLE_DSN` | an alias from `tnsnames.ora`, e.g. `petropulse_low` |
| `ORACLE_WALLET_DIR` | folder holding `tnsnames.ora` and `ewallet.pem` |
| `ORACLE_WALLET_PASSWORD` | the wallet password from this step |

## 5. Test from the backend
```powershell
cd backend ; .\.venv\Scripts\Activate.ps1
copy ..\.env.example .env        # fill in the values above (backend\.env is git-ignored)
python scripts\check_oracle.py   # prints "OK - Oracle connection and schema verified."
$env:RUN_ORACLE_TESTS="1" ; python -m pytest tests\test_oracle_live.py -v   # full live flow; deletes its own test user
$env:DEMO_PASSWORD="ChooseADemoPassword1" ; python -m app.seed             # optional demo data (user demo@petropulse.example)
python -m app.seed --remove      # removes only the demo user's data
```
Seed and live-test never touch real accounts. The app never creates or resets tables at start-up.

## 6. Verify persistence (SQL)
```sql
SELECT u.email, COUNT(DISTINCT w.id) wells, COUNT(p.id) records
FROM pp_users u LEFT JOIN pp_wells w ON w.user_id = u.id LEFT JOIN pp_production p ON p.well_id = w.id GROUP BY u.email;
```
## Troubleshooting
`DPY-6005`/timeout: wrong DSN alias, wallet dir, or no internet · `DPY-4011`/`ORA-01017`: wrong user/password · `ORA-00942` table not found: scripts not run as `petropulse_app` · wallet password errors: `ORACLE_WALLET_PASSWORD` must be the one chosen at download.
