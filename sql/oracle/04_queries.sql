-- PetroPulse 2.0 | 04_queries.sql | SELECT, filtering, sorting, JOIN, GROUP BY, HAVING, subqueries
-- Same formulas as backend/app/calculations.py:
--   shortfall = planned - actual | achievement % = actual/planned*100 | revenue = actual*price | revenue loss = GREATEST(planned-actual,0)*price

-- 1. Filtering and sorting: records below plan in the last 7 days, worst first
SELECT w.well_code, p.production_date, p.planned_oil, p.actual_oil, p.planned_oil - p.actual_oil AS shortfall_bbl
FROM pp_production p JOIN pp_wells w ON w.id = p.well_id
WHERE p.actual_oil < p.planned_oil AND p.production_date >= TRUNC(SYSDATE) - 7
ORDER BY shortfall_bbl DESC;

-- 2. Per-record metrics (achievement, revenue, profit, revenue loss). NULLIF makes zero planned production safe.
SELECT w.well_code, p.production_date,
       ROUND(p.actual_oil / NULLIF(p.planned_oil, 0) * 100, 2)  AS achievement_pct,
       p.actual_oil * p.oil_price                               AS revenue_usd,
       p.actual_oil * p.oil_price - p.operating_cost            AS operating_profit_usd,
       GREATEST(p.planned_oil - p.actual_oil, 0) * p.oil_price  AS revenue_loss_usd
FROM pp_production p JOIN pp_wells w ON w.id = p.well_id
ORDER BY p.production_date DESC, w.well_code;

-- 3. GROUP BY with aggregates: totals per well (positive shortfall is summed per record)
SELECT w.well_code, COUNT(*) AS records, SUM(p.planned_oil) AS planned_bbl, SUM(p.actual_oil) AS actual_bbl,
       ROUND(SUM(p.actual_oil) / NULLIF(SUM(p.planned_oil), 0) * 100, 2) AS achievement_pct,
       SUM(GREATEST(p.planned_oil - p.actual_oil, 0))                    AS positive_shortfall_bbl,
       SUM(GREATEST(p.planned_oil - p.actual_oil, 0) * p.oil_price)      AS revenue_loss_usd
FROM pp_production p JOIN pp_wells w ON w.id = p.well_id
GROUP BY w.well_code ORDER BY revenue_loss_usd DESC;

-- 4. HAVING: wells whose achievement is below 85 %
SELECT w.well_code, ROUND(SUM(p.actual_oil) / NULLIF(SUM(p.planned_oil), 0) * 100, 2) AS achievement_pct
FROM pp_production p JOIN pp_wells w ON w.id = p.well_id
GROUP BY w.well_code
HAVING SUM(p.actual_oil) / NULLIF(SUM(p.planned_oil), 0) * 100 < 85;

-- 5. Subquery: records whose shortfall is above the average shortfall of all records
SELECT w.well_code, p.production_date, p.planned_oil - p.actual_oil AS shortfall_bbl
FROM pp_production p JOIN pp_wells w ON w.id = p.well_id
WHERE p.planned_oil - p.actual_oil > (SELECT AVG(planned_oil - actual_oil) FROM pp_production)
ORDER BY shortfall_bbl DESC;

-- 6. Monthly summary
SELECT TO_CHAR(production_date, 'YYYY-MM') AS month, SUM(planned_oil) AS planned_bbl, SUM(actual_oil) AS actual_bbl,
       SUM(actual_oil * oil_price) AS revenue_usd, SUM(operating_cost) AS cost_usd, SUM(actual_oil * oil_price) - SUM(operating_cost) AS profit_usd
FROM pp_production GROUP BY TO_CHAR(production_date, 'YYYY-MM') ORDER BY month;

-- 7. Loss by RECORDED cause (only where a cause was entered)
SELECT loss_category, COUNT(*) AS days, SUM(GREATEST(planned_oil - actual_oil, 0)) AS positive_shortfall_bbl
FROM pp_production WHERE loss_category IS NOT NULL GROUP BY loss_category ORDER BY positive_shortfall_bbl DESC;

-- 8. Wells with no production records at all (anti-join with NOT EXISTS)
SELECT w.well_code FROM pp_wells w WHERE NOT EXISTS (SELECT 1 FROM pp_production p WHERE p.well_id = w.id);

-- 9. Verification queries for a deployed system (run as the app user)
SELECT table_name FROM user_tables WHERE table_name LIKE 'PP\_%' ESCAPE '\' ORDER BY table_name;
SELECT u.email, COUNT(DISTINCT w.id) AS wells, COUNT(p.id) AS records
FROM pp_users u LEFT JOIN pp_wells w ON w.user_id = u.id LEFT JOIN pp_production p ON p.well_id = w.id GROUP BY u.email ORDER BY u.email;
