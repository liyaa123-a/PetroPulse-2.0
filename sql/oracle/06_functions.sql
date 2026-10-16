-- PetroPulse 2.0 | 06_functions.sql | Stored functions (same formulas as the Python backend)

CREATE OR REPLACE FUNCTION fn_achievement_pct (p_planned IN NUMBER, p_actual IN NUMBER) RETURN NUMBER DETERMINISTIC IS
BEGIN
    IF p_planned IS NULL OR p_planned = 0 THEN RETURN NULL; END IF;   -- zero planned production is handled safely
    RETURN ROUND(p_actual / p_planned * 100, 2);
END fn_achievement_pct;
/

CREATE OR REPLACE FUNCTION fn_revenue_loss (p_planned IN NUMBER, p_actual IN NUMBER, p_price IN NUMBER) RETURN NUMBER DETERMINISTIC IS
BEGIN
    RETURN GREATEST(p_planned - p_actual, 0) * p_price;   -- overproduction never produces a negative loss
END fn_revenue_loss;
/

-- Total estimated revenue loss for one well between two dates.
CREATE OR REPLACE FUNCTION fn_well_revenue_loss (p_well_id IN NUMBER, p_from IN DATE, p_to IN DATE) RETURN NUMBER IS
    v_loss NUMBER;
BEGIN
    SELECT NVL(SUM(fn_revenue_loss(planned_oil, actual_oil, oil_price)), 0) INTO v_loss
    FROM pp_production WHERE well_id = p_well_id AND production_date BETWEEN p_from AND p_to;
    RETURN v_loss;
END fn_well_revenue_loss;
/

-- Demo:
-- SELECT well_code, fn_achievement_pct(SUM(planned_oil), SUM(actual_oil)) AS achievement FROM pp_production p JOIN pp_wells w ON w.id = p.well_id GROUP BY well_code;
-- SELECT fn_well_revenue_loss(id, TRUNC(SYSDATE) - 30, TRUNC(SYSDATE)) FROM pp_wells;
