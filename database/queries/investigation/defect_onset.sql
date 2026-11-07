-- Investigation query: Hourly defect rate with previous-hour comparison
-- Business question: When did a machine's defect rate start to rise?
-- Tables: inspections, production_units, production_batches
-- Techniques: CTE, DATE_FORMAT hourly bucketing, LAG() and cumulative SUM()
--   window functions over an ordered frame
-- Parameters: :machine_id, :window_start, :window_end
-- Result: one row per hour bucket with defect_rate, previous_bucket_rate,
--   cumulative_rate. The engine picks the first bucket at or above threshold.
--   Hours with no inspections produce no row, so previous_bucket_rate is the
--   rate of the previous non-empty hour (LAG over the rows that exist), not
--   necessarily the rate of the clock hour before.
-- Used by: rule R3 (defect-rate onset); the four-day investigation window.
-- Performance: EXPLAIN at demo volume (1,400 inspections, 35 batches) with
--   :machine_id = 3 reads production_batches by ref on
--   ix_production_batches_machine_time (12 rows, "Using index; Using
--   temporary"), units by ref on uq_unit_batch_sequence (20 per batch, "Using
--   index"), and inspections by ref on uq_inspection_unit_spec (2 per unit)
--   with the time filter as "Using where"; ix_inspections_time_result,
--   ix_inspections_time_id, and ix_inspections_spec_time are in possible_keys
--   but not chosen because the machine filter is the selective predicate.
--   The CTE groups 480 inspections (240 units of CNC-03) into 7 hour buckets,
--   and the LAG and SUM window functions run over those 7 rows.
WITH hourly AS (
    SELECT
        DATE_FORMAT(i.inspected_at, '%Y-%m-%dT%H:00:00') AS bucket_start,
        COUNT(i.id)          AS inspected,
        SUM(i.result = 'FAIL') AS failed
    FROM inspections i
    JOIN production_units   u ON u.id = i.unit_id
    JOIN production_batches b ON b.id = u.batch_id
    WHERE b.machine_id = :machine_id
      AND i.inspected_at >= :window_start
      AND i.inspected_at <  :window_end
    GROUP BY bucket_start
)
SELECT
    bucket_start,
    inspected,
    failed,
    ROUND(failed / inspected, 4)                                   AS defect_rate,
    ROUND(LAG(failed / inspected) OVER (ORDER BY bucket_start), 4) AS previous_bucket_rate,
    ROUND(SUM(failed) OVER (ORDER BY bucket_start)
          / SUM(inspected) OVER (ORDER BY bucket_start), 4)        AS cumulative_rate
FROM hourly
ORDER BY bucket_start;
