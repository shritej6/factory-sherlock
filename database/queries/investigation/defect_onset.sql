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
