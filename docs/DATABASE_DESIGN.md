# Database design (Oracle)

Tables: `PP_USERS` 1—N `PP_WELLS` 1—N `PP_PRODUCTION`; `PP_WELLS` 1—N `PP_TARGETS`; `PP_USERS` 1—N `PP_ALERTS` (optionally linked to a well and a production record).
```
PP_USERS(id PK, email UQ, full_name, password_hash, token_version, is_demo, 5 alert thresholds, created_at, updated_at)
PP_WELLS(id PK, user_id FK, well_code, well_name, field_name, well_type, status, description, …)  UQ(user_id, well_code), UQ(id, user_id)
PP_PRODUCTION(id PK, user_id FK, well_id, production_date, planned_oil, actual_oil, oil_price, operating_cost, downtime_hours, loss_category, notes, …)
     UQ(well_id, production_date)  FK(well_id, user_id) → PP_WELLS(id, user_id)
PP_TARGETS(id PK, user_id FK, well_id, daily_target_oil, start_date, end_date, notes, …)  FK(well_id, user_id) → PP_WELLS(id, user_id)
PP_ALERTS(id PK, user_id FK, well_id, record_id FK, rule_code, severity, message, trigger_reason, alert_date, status, dedupe_key, …)  UQ(user_id, dedupe_key)
```
Design decisions
- **Ownership is enforced by the database**: production and targets reference wells by the *pair* `(id, user_id)`, so a record can never point to another user's well, even if application code had a bug.
- **No duplicate daily records**: `UQ(well_id, production_date)` (one record per well per day; no shifts).
- **Check constraints** keep volumes/prices ≥ 0, downtime 0–24 h, valid enums for type, status, severity, alert status, and `end_date >= start_date`.
- **Indexes** on `(user_id, production_date)`, well, target periods and alert status support the dashboard/filter queries.
- **Deletion**: wells are archived (status), never deleted, so history is preserved. Account deletion removes alerts → targets → production → wells → user in one transaction (explicit order; no cascade surprises). Retention policy: deleting an account deletes all of its data.
- **Types**: `NUMBER(14,2)` for volumes/money (Python uses `Decimal`, rounding only for display), `DATE` for production days, `TIMESTAMP` for audit times, identity columns for keys.
- Overlapping targets for one well are rejected by the API (documented rule); unit conventions: bbl, USD per bbl, hours.
- Loss causes (`loss_category`) are only what the user recorded; the system never infers an engineering cause.
