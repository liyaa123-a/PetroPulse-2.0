-- PetroPulse 2.0 | 07_cursors.sql | Explicit cursor, cursor with WHERE, parameterised cursor
SET SERVEROUTPUT ON

-- 1. Explicit cursor: print every well with its totals
DECLARE
    CURSOR c_wells IS
        SELECT w.well_code, SUM(p.planned_oil) AS planned, SUM(p.actual_oil) AS actual
        FROM pp_wells w JOIN pp_production p ON p.well_id = w.id GROUP BY w.well_code ORDER BY w.well_code;
    v_row c_wells%ROWTYPE;
BEGIN
    OPEN c_wells;
    LOOP
        FETCH c_wells INTO v_row;
        EXIT WHEN c_wells%NOTFOUND;
        DBMS_OUTPUT.PUT_LINE(RPAD(v_row.well_code, 12) || ' planned=' || v_row.planned || ' actual=' || v_row.actual
                             || ' achievement=' || fn_achievement_pct(v_row.planned, v_row.actual) || '%');
    END LOOP;
    CLOSE c_wells;
END;
/

-- 2. Cursor with a WHERE condition: only records below plan
DECLARE
    CURSOR c_short IS
        SELECT w.well_code, p.production_date, p.planned_oil - p.actual_oil AS shortfall
        FROM pp_production p JOIN pp_wells w ON w.id = p.well_id
        WHERE p.actual_oil < p.planned_oil ORDER BY shortfall DESC;
BEGIN
    FOR r IN c_short LOOP
        DBMS_OUTPUT.PUT_LINE(r.well_code || ' ' || TO_CHAR(r.production_date, 'YYYY-MM-DD') || ' short by ' || r.shortfall || ' bbl');
    END LOOP;
END;
/

-- 3. Parameterised cursor: records of one well in a date range, with a running count
DECLARE
    CURSOR c_well_days (p_code VARCHAR2, p_from DATE, p_to DATE) IS
        SELECT p.production_date, p.planned_oil, p.actual_oil, p.oil_price
        FROM pp_production p JOIN pp_wells w ON w.id = p.well_id
        WHERE w.well_code = p_code AND p.production_date BETWEEN p_from AND p_to ORDER BY p.production_date;
    v_n NUMBER := 0;
    v_loss NUMBER := 0;
BEGIN
    FOR r IN c_well_days('ALPHA-01', TRUNC(SYSDATE) - 30, TRUNC(SYSDATE)) LOOP
        v_n := v_n + 1;
        v_loss := v_loss + fn_revenue_loss(r.planned_oil, r.actual_oil, r.oil_price);
    END LOOP;
    DBMS_OUTPUT.PUT_LINE('ALPHA-01: ' || v_n || ' records, estimated revenue loss USD ' || v_loss);
EXCEPTION
    WHEN OTHERS THEN DBMS_OUTPUT.PUT_LINE('Cursor error: ' || SQLERRM);
END;
/
