-- Investigation query: Hourly defect rates for one machine
-- Business question: Hour by hour, how many units did a machine inspect and
--   how many failed, so that a statistical onset test can be run over them?
-- Tables: inspections, production_units, production_batches
-- Techniques: DATE_FORMAT hourly bucketing, conditional SUM over a boolean
--   expression, half-open time window (>= start AND < end)
-- Parameters: :machine_id, :window_start, :window_end
-- Result: one row per hour bucket, oldest first, with inspected_count,
--   failed_count and defect_rate (ROUND to 4 places). Hours with no
--   inspections are simply absent: there is no calendar scaffold, so the
--   consumer sees the hours that exist and should not assume consecutive
--   clock hours. Rule R7 appends two derived columns (cusum, signal) to these
--   rows in Python; the SQL itself returns only the counts and the rate.
-- Used by: rule R7 (CUSUM onset detection). Rule R3 uses defect_onset.sql,
--   which buckets the same way but adds LAG and cumulative columns.
SELECT
    DATE_FORMAT(i.inspected_at, '%Y-%m-%dT%H:00:00')     AS bucket_start,
    COUNT(i.id)                                           AS inspected_count,
    SUM(i.result = 'FAIL')                                AS failed_count,
    ROUND(SUM(i.result = 'FAIL') / COUNT(i.id), 4)        AS defect_rate
FROM inspections i
JOIN production_units   u ON u.id = i.unit_id
JOIN production_batches b ON b.id = u.batch_id
WHERE b.machine_id = :machine_id
  AND i.inspected_at >= :window_start
  AND i.inspected_at <  :window_end
GROUP BY bucket_start
ORDER BY bucket_start;
