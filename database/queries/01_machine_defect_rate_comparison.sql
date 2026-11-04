-- Query 01: Machine defect-rate comparison
-- Business question: Which machines produced the highest share of failed
--   inspections during a time window, and how does each compare with the fleet?
-- Tables: machines, production_batches, production_units, inspections
-- Techniques: CTE that filters inspections by time and aggregates per machine
--   before the machines table is joined, LEFT JOIN so a machine with no
--   inspections still appears, conditional aggregation, window functions
--   (SUM OVER, RANK OVER), NULLIF to avoid division by zero
-- Parameters: :window_start, :window_end (DATETIME, half-open interval)
-- Result: one row per machine with inspected, failed, defect_rate,
--   fleet_defect_rate, and defect_rank (1 = worst; a machine with no
--   inspections in the window has a NULL defect_rate and ranks last)
-- Used by: analytics dashboard, investigation rule R1
-- Performance: EXPLAIN at demo volume (1,400 inspections, all inside the
--   four-day window) drives the derived table from production_batches with an
--   index scan of ix_production_batches_machine_time (35 rows), units by ref
--   on uq_unit_batch_sequence, and inspections by ref on
--   uq_inspection_unit_spec with the time filter applied as "Using where";
--   ix_inspections_time_result is in possible_keys but not chosen. With a
--   one-hour window the derived table becomes a range scan on
--   ix_inspections_time_result (240 rows) followed by eq_ref lookups to units
--   and batches. machines (3 rows) is then joined to the grouped rows through
--   the derived table's auto key, with one filesort for the final ORDER BY.
WITH window_inspections AS (
    SELECT
        b.machine_id,
        COUNT(i.id)                         AS inspected,
        COALESCE(SUM(i.result = 'FAIL'), 0) AS failed
    FROM inspections i
    JOIN production_units   u ON u.id = i.unit_id
    JOIN production_batches b ON b.id = u.batch_id
    WHERE i.inspected_at >= :window_start
      AND i.inspected_at <  :window_end
    GROUP BY b.machine_id
)
SELECT
    m.id   AS machine_id,
    m.code AS machine_code,
    m.name AS machine_name,
    COALESCE(wi.inspected, 0) AS inspected,
    COALESCE(wi.failed, 0)    AS failed,
    ROUND(wi.failed / NULLIF(wi.inspected, 0), 4)                            AS defect_rate,
    ROUND(SUM(wi.failed) OVER () / NULLIF(SUM(wi.inspected) OVER (), 0), 4) AS fleet_defect_rate,
    RANK() OVER (ORDER BY wi.failed / NULLIF(wi.inspected, 0) DESC)          AS defect_rank
FROM machines m
LEFT JOIN window_inspections wi ON wi.machine_id = m.id
ORDER BY defect_rank, machine_code;
