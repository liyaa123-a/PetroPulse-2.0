# Deployment guide: GitHub → Oracle → Render → Vercel

Nothing here has been deployed for you: the accounts are yours. Free tiers have quotas, can change, and may require a card. Render's free web service **sleeps after ~15 minutes idle** (first request can take ~30–60 s); Oracle free-tier limits and availability vary.

## A. GitHub
```powershell
cd C:\Projects\PetroPulse_2.0
git init ; git branch -M main
git status                              # confirm NO .env, wallet, .pem, node_modules or dist appear
git check-ignore -v backend\.env ewallet.pem   # both should be reported as ignored
git add . ; git commit -m "PetroPulse 2.0"
git remote add origin https://github.com/<you>/petropulse.git   # create the EMPTY repo on github.com first
git push -u origin main
```
If you reuse an existing repository, push to a **new branch** (`git push origin main:petropulse`) instead of overwriting unrelated work. If a secret was ever committed, rotate it — deleting the file later is not enough.

## B. Oracle
Follow [ORACLE_SETUP.md](ORACLE_SETUP.md) first: database, `petropulse_app` user, schema, wallet (`tnsnames.ora` + `ewallet.pem`).

## C. Render (backend)
1. render.com → **New** → **Web Service** → connect the GitHub repo (or **Blueprint** to use `render.yaml`).
2. Settings: **Root Directory** `backend` · **Runtime** Python · **Build Command** `pip install -r requirements.txt` · **Start Command** `gunicorn -c gunicorn.conf.py wsgi:app` (binds `0.0.0.0:$PORT`) · **Health Check Path** `/api/health/live` · env var `PYTHON_VERSION=3.12.7`.
3. **Environment** variables: `APP_ENV=production`, `SECRET_KEY` (random, ≥32 chars; PowerShell: `-join ((48..57)+(65..90)+(97..122) | Get-Random -Count 48 | % {[char]$_})`), `FRONTEND_ORIGIN` (fill after step D; for now `https://placeholder.invalid`), `ORACLE_USER`, `ORACLE_PASSWORD`, `ORACLE_DSN`, `ORACLE_WALLET_DIR=/etc/secrets`, `ORACLE_WALLET_PASSWORD`.
4. **Secret Files** (Environment tab): add `tnsnames.ora` and `ewallet.pem`, pasting each file's contents. Render exposes them at `/etc/secrets/<name>`. They are never in Git. *Fallback:* base64 the whole wallet zip into `ORACLE_WALLET_B64` (`[Convert]::ToBase64String([IO.File]::ReadAllBytes("Wallet_PETROPULSE.zip"))`) and unset `ORACLE_WALLET_DIR` — env vars are less protected than secret files, so prefer secret files.
5. **Create Web Service**. Watch **Logs** for the build and for `Listening at: http://0.0.0.0:<port>`.
6. Test: open `https://<service>.onrender.com/api/health` → `{"database":"connected","status":"ok"}`. If it returns `503` / `"database":"unavailable"`, the Oracle settings or wallet are wrong — read the Render logs (details are logged there, never returned to clients).

## D. Vercel (frontend)
1. vercel.com → **Add New… → Project** → import the GitHub repo.
2. **Root Directory** `frontend` · **Framework Preset** Vite · **Install Command** `npm install` · **Build Command** `npm run build` · **Output Directory** `dist`.
3. **Environment Variables:** `VITE_API_BASE_URL` = `https://<service>.onrender.com` (https, no trailing slash). Only this one — never put Oracle or backend secrets in Vercel.
4. **Deploy** and copy the URL (e.g. `https://petropulse.vercel.app`). `frontend/vercel.json` rewrites every path to `index.html`, so refreshing `/wells` or `/loss` works. Changing an env var requires **Redeploy**.

## E. Connect them
In Render → Environment, set `FRONTEND_ORIGIN` to the exact Vercel origin (`https://petropulse.vercel.app`, no trailing slash; several origins may be comma-separated, e.g. add a custom domain). Save → Render restarts. Preview-deployment URLs on Vercel are different origins and will be blocked unless you add them.
If the browser shows a CORS error: check the origin spelling/`https`, then DevTools → Network → the failing request → response headers must contain `Access-Control-Allow-Origin` equal to your site. If requests go to `localhost`, `VITE_API_BASE_URL` was missing at **build** time — set it and redeploy. (The built JS contains no `localhost`; this was checked.)

## F. Live checklist
1. Open the Vercel URL. 2. Register. 3. Sign in. 4. Add a well. 5. Add a production record. 6. In Oracle: `SELECT * FROM pp_production ORDER BY id DESC FETCH FIRST 5 ROWS ONLY;` — the row is there. 7. Refresh the page and sign in again; the data remains. 8. Open **Dashboard**: check achievement, shortfall, revenue, loss against your numbers by hand (e.g. planned 1000, actual 800, $70 → 80 %, 200 bbl, $56,000, $14,000). 9. Open **Loss analysis**. 10. **Export CSV**. 11. Sign out. 12. Register a second account → it sees no wells/records of the first. 13. Redeploy/restart Render (Manual Deploy) and confirm the data is unchanged — it lives in Oracle, not on Render's disk.
API smoke test: `curl https://<service>.onrender.com/api/health` and `curl -i https://<service>.onrender.com/api/wells` (expect `401`).

## Costs and limits
Vercel Hobby, Render Free and Oracle Always Free are the intended free path, subject to their current terms. Render free instances sleep; Oracle may reclaim idle Always-Free databases (see Oracle's current policy), so log in occasionally. Nothing in this project silently adds a paid dependency.
