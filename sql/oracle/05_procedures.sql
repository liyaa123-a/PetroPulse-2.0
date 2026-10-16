-- PetroPulse 2.0 | 05_procedures.sql | Stored procedures with exception handling, COMMIT and ROLLBACK
SET SERVEROUTPUT ON

-- Add one production record for a user's well (checks ownership, archived status and validity).
CREATE OR REPLACE PROCEDURE sp_add_production (
    p_user_id IN NUMBER, p_well_code IN VARCHAR2, p_date IN DATE,
    p_planned IN NUMBER, p_actual IN NUMBER, p_price IN NUMBER, p_cost IN NUMBER DEFAULT 0
) AS
    v_well_id pp_wells.id%TYPE;
    v_status  pp_wells.status%TYPE;
    e_invalid EXCEPTION;
BEGIN
    IF p_planned < 0 OR p_actual < 0 OR p_price < 0 OR p_cost < 0 THEN
        RAISE e_invalid;
    END IF;
    SELECT id, status INTO v_well_id, v_status FROM pp_wells WHERE user_id = p_user_id AND well_code = UPPER(p_well_code);
    IF v_status = 'ARCHIVED' THEN
        RAISE_APPLICATION_ERROR(-20002, 'Well ' || p_well_code || ' is archived.');
    END IF;
    INSERT INTO pp_production (user_id, well_id, production_date, planned_oil, actual_oil, oil_price, operating_cost)
    VALUES (p_user_id, v_well_id, TRUNC(p_date), p_planned, p_actual, p_price, p_cost);
    COMMIT;
    DBMS_OUTPUT.PUT_LINE('Record saved for ' || p_well_code || ' on ' || TO_CHAR(p_date, 'YYYY-MM-DD'));
EXCEPTION
    WHEN NO_DATA_FOUND THEN
        ROLLBACK; DBMS_OUTPUT.PUT_LINE('No well ' || p_well_code || ' for this user.');
    WHEN DUP_VAL_ON_INDEX THEN
        ROLLBACK; DBMS_OUTPUT.PUT_LINE('A record already exists for that well and date.');
    WHEN e_invalid THEN
        ROLLBACK; DBMS_OUTPUT.PUT_LINE('Volumes, price and cost must not be negative.');
    WHEN OTHERS THEN
        ROLLBACK; DBMS_OUTPUT.PUT_LINE('Unexpected error: ' || SQLERRM);
END sp_add_production;
/

-- Archive a well (history is kept) and report how many production records it still has.
CREATE OR REPLACE PROCEDURE sp_archive_well (p_user_id IN NUMBER, p_well_code IN VARCHAR2) AS
    v_records NUMBER;
BEGIN
    UPDATE pp_wells SET status = 'ARCHIVED', updated_at = SYSTIMESTAMP WHERE user_id = p_user_id AND well_code = UPPER(p_well_code);
    IF SQL%ROWCOUNT = 0 THEN
        RAISE_APPLICATION_ERROR(-20001, 'Well not found for this user.');
    END IF;
    SELECT COUNT(*) INTO v_records FROM pp_production p JOIN pp_wells w ON w.id = p.well_id WHERE w.user_id = p_user_id AND w.well_code = UPPER(p_well_code);
    COMMIT;
    DBMS_OUTPUT.PUT_LINE(p_well_code || ' archived; ' || v_records || ' historical records preserved.');
EXCEPTION
    WHEN OTHERS THEN ROLLBACK; RAISE;
END sp_archive_well;
/

-- Demo (replace 1 with a real PP_USERS.ID, e.g. SELECT id FROM pp_users WHERE email = 'sqldemo@petropulse.example'):
-- EXEC sp_add_production(1, 'ALPHA-01', SYSDATE + 1, 1200, 1100, 71.4, 6200);
-- EXEC sp_archive_well(1, 'CHARLIE-03');
