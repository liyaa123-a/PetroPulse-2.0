-- PetroPulse 2.0 | 02_constraints_indexes.sql | Primary/foreign/unique/check constraints and indexes
-- Ownership integrity: pp_production and pp_targets reference pp_wells by (id, user_id), so a record can
-- never point at a well that belongs to a different user - the database enforces it, not just the API.

ALTER TABLE pp_users      ADD CONSTRAINT pk_pp_users      PRIMARY KEY (id);
ALTER TABLE pp_wells      ADD CONSTRAINT pk_pp_wells      PRIMARY KEY (id);
ALTER TABLE pp_production ADD CONSTRAINT pk_pp_production PRIMARY KEY (id);
ALTER TABLE pp_targets    ADD CONSTRAINT pk_pp_targets    PRIMARY KEY (id);
ALTER TABLE pp_alerts     ADD CONSTRAINT pk_pp_alerts     PRIMARY KEY (id);

ALTER TABLE pp_users      ADD CONSTRAINT uq_pp_users_email   UNIQUE (email);
ALTER TABLE pp_wells      ADD CONSTRAINT uq_pp_wells_code    UNIQUE (user_id, well_code);
ALTER TABLE pp_wells      ADD CONSTRAINT uq_pp_wells_id_user UNIQUE (id, user_id);
ALTER TABLE pp_production ADD CONSTRAINT uq_pp_prod_well_day UNIQUE (well_id, production_date);
ALTER TABLE pp_alerts     ADD CONSTRAINT uq_pp_alerts_key    UNIQUE (user_id, dedupe_key);

ALTER TABLE pp_wells      ADD CONSTRAINT fk_wells_user  FOREIGN KEY (user_id) REFERENCES pp_users (id);
ALTER TABLE pp_production ADD CONSTRAINT fk_prod_user   FOREIGN KEY (user_id) REFERENCES pp_users (id);
ALTER TABLE pp_production ADD CONSTRAINT fk_prod_well   FOREIGN KEY (well_id, user_id) REFERENCES pp_wells (id, user_id);
ALTER TABLE pp_targets    ADD CONSTRAINT fk_tgt_user    FOREIGN KEY (user_id) REFERENCES pp_users (id);
ALTER TABLE pp_targets    ADD CONSTRAINT fk_tgt_well    FOREIGN KEY (well_id, user_id) REFERENCES pp_wells (id, user_id);
ALTER TABLE pp_alerts     ADD CONSTRAINT fk_alert_user  FOREIGN KEY (user_id) REFERENCES pp_users (id);
ALTER TABLE pp_alerts     ADD CONSTRAINT fk_alert_rec   FOREIGN KEY (record_id) REFERENCES pp_production (id);

ALTER TABLE pp_users ADD CONSTRAINT ck_users_demo   CHECK (is_demo IN (0, 1));
ALTER TABLE pp_users ADD CONSTRAINT ck_users_thr    CHECK (achievement_threshold BETWEEN 1 AND 100 AND downtime_threshold_hours BETWEEN 0 AND 24
                                                       AND repeat_miss_count BETWEEN 2 AND 30 AND missing_record_days BETWEEN 1 AND 60 AND target_at_risk_pct BETWEEN 1 AND 100);
ALTER TABLE pp_wells ADD CONSTRAINT ck_wells_type   CHECK (well_type IN ('VERTICAL', 'HORIZONTAL', 'DIRECTIONAL', 'OFFSHORE'));
ALTER TABLE pp_wells ADD CONSTRAINT ck_wells_status CHECK (status IN ('ACTIVE', 'SHUT_IN', 'MAINTENANCE', 'ARCHIVED'));
ALTER TABLE pp_production ADD CONSTRAINT ck_prod_vol  CHECK (planned_oil >= 0 AND actual_oil >= 0);
ALTER TABLE pp_production ADD CONSTRAINT ck_prod_money CHECK (oil_price >= 0 AND operating_cost >= 0);
ALTER TABLE pp_production ADD CONSTRAINT ck_prod_down CHECK (downtime_hours BETWEEN 0 AND 24);
ALTER TABLE pp_targets ADD CONSTRAINT ck_tgt_value  CHECK (daily_target_oil > 0);
ALTER TABLE pp_targets ADD CONSTRAINT ck_tgt_period CHECK (end_date >= start_date);
ALTER TABLE pp_alerts ADD CONSTRAINT ck_alert_sev   CHECK (severity IN ('INFO', 'WARNING', 'CRITICAL'));
ALTER TABLE pp_alerts ADD CONSTRAINT ck_alert_stat  CHECK (status IN ('NEW', 'ACKNOWLEDGED', 'RESOLVED'));

CREATE INDEX ix_prod_user_date ON pp_production (user_id, production_date);
CREATE INDEX ix_prod_well      ON pp_production (well_id);
CREATE INDEX ix_wells_user     ON pp_wells (user_id, status);
CREATE INDEX ix_tgt_well       ON pp_targets (well_id, start_date, end_date);
CREATE INDEX ix_alert_user     ON pp_alerts (user_id, status, alert_date);
CREATE INDEX ix_alert_rec      ON pp_alerts (record_id);
