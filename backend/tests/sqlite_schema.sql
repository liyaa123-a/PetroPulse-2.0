-- TEST-ONLY SQLite mirror of sql/oracle/01_schema.sql + 02_constraints_indexes.sql. Never used by the deployed service.
PRAGMA foreign_keys = ON;
CREATE TABLE pp_users (
  id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT NOT NULL UNIQUE, full_name TEXT NOT NULL, password_hash TEXT NOT NULL,
  token_version INTEGER NOT NULL DEFAULT 0, is_demo INTEGER NOT NULL DEFAULT 0 CHECK (is_demo IN (0,1)),
  achievement_threshold NUMERIC NOT NULL DEFAULT 85, downtime_threshold_hours NUMERIC NOT NULL DEFAULT 8,
  repeat_miss_count INTEGER NOT NULL DEFAULT 3, missing_record_days INTEGER NOT NULL DEFAULT 2, target_at_risk_pct NUMERIC NOT NULL DEFAULT 90,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE pp_wells (
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES pp_users(id), well_code TEXT NOT NULL, well_name TEXT NOT NULL,
  field_name TEXT NOT NULL, well_type TEXT NOT NULL DEFAULT 'VERTICAL' CHECK (well_type IN ('VERTICAL','HORIZONTAL','DIRECTIONAL','OFFSHORE')),
  status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','SHUT_IN','MAINTENANCE','ARCHIVED')), description TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL, UNIQUE (user_id, well_code), UNIQUE (id, user_id));
CREATE TABLE pp_production (
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES pp_users(id), well_id INTEGER NOT NULL, production_date TEXT NOT NULL,
  planned_oil NUMERIC NOT NULL CHECK (planned_oil >= 0), actual_oil NUMERIC NOT NULL CHECK (actual_oil >= 0), oil_price NUMERIC NOT NULL CHECK (oil_price >= 0),
  operating_cost NUMERIC NOT NULL DEFAULT 0 CHECK (operating_cost >= 0), downtime_hours NUMERIC DEFAULT 0 CHECK (downtime_hours BETWEEN 0 AND 24),
  loss_category TEXT, notes TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
  UNIQUE (well_id, production_date), FOREIGN KEY (well_id, user_id) REFERENCES pp_wells (id, user_id));
CREATE TABLE pp_targets (
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES pp_users(id), well_id INTEGER NOT NULL, daily_target_oil NUMERIC NOT NULL CHECK (daily_target_oil > 0),
  start_date TEXT NOT NULL, end_date TEXT NOT NULL, notes TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, CHECK (end_date >= start_date),
  FOREIGN KEY (well_id, user_id) REFERENCES pp_wells (id, user_id));
CREATE TABLE pp_alerts (
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES pp_users(id), well_id INTEGER, record_id INTEGER REFERENCES pp_production(id),
  rule_code TEXT NOT NULL, severity TEXT NOT NULL CHECK (severity IN ('INFO','WARNING','CRITICAL')), message TEXT NOT NULL, trigger_reason TEXT NOT NULL,
  alert_date TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'NEW' CHECK (status IN ('NEW','ACKNOWLEDGED','RESOLVED')), dedupe_key TEXT NOT NULL,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL, UNIQUE (user_id, dedupe_key));
