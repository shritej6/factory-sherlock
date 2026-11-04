-- Query 08: Batches requiring quality review
-- Business question: Which batches in a window have a defect rate at or above a
--   threshold, are not already quarantined, and have (or have not) already been
--   attached to an investigation?
-- Tables: production_batches, machines, production_orders, products,
--   production_units, inspections, investigation_batches
-- Techniques: CTE, aggregation with HAVING-style filter in the outer query,
--   EXISTS correlated subquery, optional machine filter. The threshold is
--   compared with the unrounded failed/inspected ratio; defect_rate in the
--   output is rounded to four places for display only.
-- Parameters: :window_start, :window_end, :threshold (0.0 to 1.0),
--   :machine_id (NULL for all machines)
-- Result: one row per batch above threshold, worst first
-- Used by: investigation rule R5 (affected batches), quality screen
-- Performance: EXPLAIN at demo volume with :machine_id = NULL: a full scan
--   of production_batches (ALL, 35 rows) with ix_production_batches_machine_time
--   in possible_keys but unused, because the (:machine_id IS NULL OR ...)
--   pattern prevents a range scan; machines, orders, and products are eq_ref
--   on their primary keys, units are ref on uq_unit_batch_sequence, and
--   inspections ref on uq_inspection_unit_spec. One temporary table for the
--   GROUP BY and a filesort for the final ORDER BY. The EXISTS probe is a
--   DEPENDENT SUBQUERY on the batch_id index of investigation_batches.
WITH batch_quality AS (
    SELECT
        b.id           AS batch_id,
        b.batch_number,
        b.status       AS batch_status,
        m.code         AS machine_code,
        p.name         AS product_name,
        b.started_at,
        COUNT(i.id)                    AS inspected,
        COALESCE(SUM(i.result = 'FAIL'), 0) AS failed
    FROM production_batches b
    JOIN machines           m ON m.id = b.machine_id
    JOIN production_orders  o ON o.id = b.production_order_id
    JOIN products           p ON p.id = o.product_id
    JOIN production_units   u ON u.batch_id = b.id
    JOIN inspections        i ON i.unit_id = u.id
    WHERE b.started_at >= :window_start
      AND b.started_at <  :window_end
      AND (:machine_id IS NULL OR b.machine_id = :machine_id)
    GROUP BY b.id, b.batch_number, b.status, m.code, p.name, b.started_at
)
SELECT
    bq.batch_id,
    bq.batch_number,
    bq.batch_status,
    bq.machine_code,
    bq.product_name,
    bq.started_at,
    bq.inspected,
    bq.failed,
    ROUND(bq.failed / NULLIF(bq.inspected, 0), 4) AS defect_rate,
    EXISTS (
        SELECT 1 FROM investigation_batches ib WHERE ib.batch_id = bq.batch_id
    ) AS already_under_investigation
FROM batch_quality bq
WHERE bq.failed / NULLIF(bq.inspected, 0) >= :threshold
  AND bq.batch_status <> 'QUARANTINED'
ORDER BY defect_rate DESC, bq.started_at;
