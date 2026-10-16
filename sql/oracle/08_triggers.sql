-- PetroPulse 2.0 | 08_triggers.sql | Triggers

-- Keep updated_at current on every UPDATE of a production record.
CREATE OR REPLACE TRIGGER trg_prod_touch
BEFORE UPDATE ON pp_production FOR EACH ROW
BEGIN
    :NEW.updated_at := SYSTIMESTAMP;
END;
/

-- Business rule enforced inside the database: no new production records for an ARCHIVED well.
CREATE OR REPLACE TRIGGER trg_prod_no_archived
BEFORE INSERT ON pp_production FOR EACH ROW
DECLARE
    v_status pp_wells.status%TYPE;
BEGIN
    SELECT status INTO v_status FROM pp_wells WHERE id = :NEW.well_id;
    IF v_status = 'ARCHIVED' THEN
        RAISE_APPLICATION_ERROR(-20010, 'Cannot add production to an archived well.');
    END IF;
END;
/

-- Test (should fail with ORA-20010 once a well is archived):
-- EXEC sp_archive_well(<user_id>, 'CHARLIE-03');
-- INSERT INTO pp_production (user_id, well_id, production_date, planned_oil, actual_oil, oil_price) SELECT user_id, id, TRUNC(SYSDATE), 1, 1, 1 FROM pp_wells WHERE well_code = 'CHARLIE-03';
