-- PetroPulse 2.0 | 03_sample_data.sql | DML: INSERT / UPDATE / DELETE with transactions
-- Inserts a SQL-only demo user that CANNOT log in (its password hash is not a valid hash).
-- For a login-capable demo account use:  DEMO_PASSWORD=... python -m app.seed   (backend folder)
-- Safe to remove again with the DELETE block at the bottom (it only touches this demo user).

INSERT INTO pp_users (email, full_name, password_hash, is_demo)
VALUES ('sqldemo@petropulse.example', 'SQL Demo Operator', 'NOT-A-LOGIN-HASH', 1);

INSERT INTO pp_wells (user_id, well_code, well_name, field_name, well_type)
SELECT id, 'ALPHA-01', 'Alpha 1', 'Mesa Verde Field', 'VERTICAL'   FROM pp_users WHERE email = 'sqldemo@petropulse.example';
INSERT INTO pp_wells (user_id, well_code, well_name, field_name, well_type)
SELECT id, 'BRAVO-07', 'Bravo 7', 'Red Ridge Field',   'DIRECTIONAL' FROM pp_users WHERE email = 'sqldemo@petropulse.example';
INSERT INTO pp_wells (user_id, well_code, well_name, field_name, well_type, status)
SELECT id, 'CHARLIE-03', 'Charlie 3', 'Offshore Block C', 'OFFSHORE', 'MAINTENANCE' FROM pp_users WHERE email = 'sqldemo@petropulse.example';

-- Seven days of production for each of the first two wells (mix of shortfall and overproduction)
INSERT INTO pp_production (user_id, well_id, production_date, planned_oil, actual_oil, oil_price, operating_cost, downtime_hours, loss_category)
SELECT w.user_id, w.id, TRUNC(SYSDATE) - d.n,
       CASE w.well_code WHEN 'ALPHA-01' THEN 1200 ELSE 950 END,
       CASE w.well_code WHEN 'ALPHA-01' THEN 1200 + (MOD(d.n, 3) - 1) * 150 ELSE 950 - MOD(d.n, 4) * 120 END,
       71.40, 6200,
       CASE WHEN w.well_code = 'BRAVO-07' AND MOD(d.n, 4) = 3 THEN 10 ELSE 0 END,
       CASE WHEN w.well_code = 'BRAVO-07' AND MOD(d.n, 4) = 3 THEN 'EQUIPMENT_FAILURE' END
FROM pp_wells w
JOIN pp_users u ON u.id = w.user_id AND u.email = 'sqldemo@petropulse.example'
CROSS JOIN (SELECT LEVEL AS n FROM dual CONNECT BY LEVEL <= 7) d
WHERE w.well_code IN ('ALPHA-01', 'BRAVO-07');

INSERT INTO pp_targets (user_id, well_id, daily_target_oil, start_date, end_date, notes)
SELECT w.user_id, w.id, 1200, TRUNC(SYSDATE) - 7, TRUNC(SYSDATE) + 30, 'Quarterly target'
FROM pp_wells w WHERE w.well_code = 'ALPHA-01' AND w.user_id = (SELECT id FROM pp_users WHERE email = 'sqldemo@petropulse.example');
COMMIT;

-- UPDATE example: correct one reading, then change a well's status
UPDATE pp_production SET actual_oil = actual_oil + 50, updated_at = SYSTIMESTAMP
 WHERE well_id = (SELECT id FROM pp_wells WHERE well_code = 'BRAVO-07' AND user_id = (SELECT id FROM pp_users WHERE email = 'sqldemo@petropulse.example'))
   AND production_date = TRUNC(SYSDATE) - 1;
UPDATE pp_wells SET status = 'SHUT_IN' WHERE well_code = 'CHARLIE-03' AND user_id = (SELECT id FROM pp_users WHERE email = 'sqldemo@petropulse.example');
COMMIT;

-- DELETE with ROLLBACK: see what would be removed, then undo
DELETE FROM pp_production WHERE production_date < TRUNC(SYSDATE) - 5 AND user_id = (SELECT id FROM pp_users WHERE email = 'sqldemo@petropulse.example');
SELECT COUNT(*) AS rows_left_inside_transaction FROM pp_production;
ROLLBACK;
SELECT COUNT(*) AS rows_after_rollback FROM pp_production;

-- Remove ALL SQL-demo data (children first). Uncomment to run:
-- DELETE FROM pp_alerts     WHERE user_id = (SELECT id FROM pp_users WHERE email = 'sqldemo@petropulse.example');
-- DELETE FROM pp_targets    WHERE user_id = (SELECT id FROM pp_users WHERE email = 'sqldemo@petropulse.example');
-- DELETE FROM pp_production WHERE user_id = (SELECT id FROM pp_users WHERE email = 'sqldemo@petropulse.example');
-- DELETE FROM pp_wells      WHERE user_id = (SELECT id FROM pp_users WHERE email = 'sqldemo@petropulse.example');
-- DELETE FROM pp_users      WHERE email = 'sqldemo@petropulse.example';
-- COMMIT;
