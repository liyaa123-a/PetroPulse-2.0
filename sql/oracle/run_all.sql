-- PetroPulse 2.0 | run_all.sql | Master script. Run from THIS folder as the application user:
--   sql -s PETROPULSE_APP@<service>  (SQLcl)   or   sqlplus PETROPULSE_APP@<service> @run_all.sql
-- 01-02 create the schema, 03 loads SQL-only sample data, 04 is a set of queries,
-- 05-08 create procedures, functions and triggers, 07 runs the cursor demos.
SET ECHO ON
SET SERVEROUTPUT ON
SET DEFINE OFF
WHENEVER SQLERROR CONTINUE
@01_schema.sql
@02_constraints_indexes.sql
@06_functions.sql
@05_procedures.sql
@08_triggers.sql
@03_sample_data.sql
@04_queries.sql
@07_cursors.sql
SELECT object_name, object_type, status FROM user_objects WHERE object_name LIKE 'PP\_%' ESCAPE '\' OR object_name LIKE 'SP\_%' ESCAPE '\' OR object_name LIKE 'FN\_%' ESCAPE '\' OR object_name LIKE 'TRG\_%' ESCAPE '\' ORDER BY object_type, object_name;
