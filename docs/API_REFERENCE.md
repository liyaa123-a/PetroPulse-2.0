# API reference

Base URL: `$VITE_API_BASE_URL/api`. JSON in/out. Authenticated endpoints need `Authorization: Bearer <token>` (401 otherwise). Success: `{"data": …, "meta": {total,page,page_size}?}`. Error: `{"error": {"code","message","fields"?}}`. Statuses: 200/201 ok · 401 auth · 404 not found (also for other users' ids) · 409 conflict · 422 validation · 429 rate limit · 503 database unavailable. Dates `YYYY-MM-DD`. Oil in bbl, money in USD.

Common query filters: `from`, `to`, `well_id`, `q`, `loss_category`, `page`, `page_size` (max 100).

| Method & path | Auth | Purpose |
|---|---|---|
| GET `/health/live` · GET `/health` | no | liveness · liveness + database status (503 when Oracle unreachable) |
| POST `/auth/register` `{email, full_name, password}` | no | create account → `{token, user}` (201) |
| POST `/auth/login` `{email, password}` | no | → `{token, user}` (rate limited: 10/min/IP) |
| POST `/auth/logout` · GET `/auth/me` · POST `/auth/password` `{current_password,new_password}` | yes | revoke tokens · profile · change password (returns a new token) |
| GET/POST `/wells` · GET/PUT `/wells/{id}` · PATCH `/wells/{id}/status` `{status}` · POST `/wells/{id}/archive` | yes | wells (`q`, `status`, `include_archived`); detail includes summary + history |
| GET/POST `/production` · GET/PUT/DELETE `/production/{id}` · GET `/production/export.csv` | yes | records (`sort`=production_date, well, planned_oil, actual_oil, shortfall, oil_price, operating_cost, downtime_hours; `dir`) |
| GET `/dashboard` | yes | totals, trend, by_well, underperforming, recent, alerts |
| GET `/analytics/trends` · `/analytics/loss` · `/analytics/summary?period=day\|week\|month` · `/analytics/export.csv` | yes | analytics (same filters) |
| GET/POST `/targets` · GET/PUT/DELETE `/targets/{id}` | yes | targets (`well_id`, `daily_target_oil`, `start_date`, `end_date`, `notes`); 409 `TARGET_OVERLAP` |
| GET `/alerts` (`status`,`severity`) · GET `/alerts/summary` · POST `/alerts/evaluate` · PATCH `/alerts/{id}` `{status}` | yes | alerts: NEW / ACKNOWLEDGED / RESOLVED |
| GET/PUT `/settings` · GET `/settings/export` · DELETE `/account` `{password, confirm:"DELETE"}` | yes | profile+thresholds · JSON export · delete account and all data |

Example — create a record:
```
POST /api/production   {"well_id":1,"production_date":"2026-10-15","planned_oil":1000,"actual_oil":800,"oil_price":70,"operating_cost":1000}
201 {"data":{"id":9,"well_code":"ALPHA-01","achievement_pct":80.0,"shortfall":200.0,"positive_shortfall":200.0,"revenue":56000.0,"operating_profit":55000.0,"revenue_loss":14000.0, …}}
409 {"error":{"code":"DUPLICATE_RECORD","message":"A record already exists for this well on this date.","fields":{"production_date":"Already recorded."}}}
```
Alert rules: LOW_ACHIEVEMENT, HIGH_DOWNTIME, REPEATED_MISS, MISSING_RECORDS (thresholds in `/settings`; evaluated after each record save and on `/alerts/evaluate`; de-duplicated by key).
