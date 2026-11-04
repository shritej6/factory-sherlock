-- Query 02: Production order performance
-- Business question: For each production order, how far along is it, how long
--   did production take, and is it on time, late, or overdue?
-- Tables: production_orders, products, machines, production_batches
-- Techniques: multi-table joins, aggregation, TIMESTAMPDIFF date arithmetic,
--   CASE expressions, parameterised LIMIT
-- Parameters: :limit (INT)
-- Result: one row per order, newest first. schedule_status is ON_TIME or LATE
--   for completed orders with a due date and at least one completed batch,
--   OVERDUE for open orders past their due date, and NOT_APPLICABLE otherwise
--   (no due date, or a completed order with no completed batch to date it by)
-- Used by: production orders screen, analytics dashboard
-- Performance: ix_production_batches_order supports the batch aggregation;
--   the ORDER BY on created_at is a filesort over a small table.
SELECT
    o.id            AS order_id,
    o.order_number,
    p.name          AS product_name,
    m.code          AS machine_code,
    o.status,
    o.quantity_planned,
    o.quantity_completed,
    ROUND(100 * o.quantity_completed / o.quantity_planned, 1) AS completion_pct,
    COUNT(b.id)        AS batch_count,
    MIN(b.started_at)  AS first_batch_started,
    MAX(b.completed_at) AS last_batch_completed,
    TIMESTAMPDIFF(MINUTE, MIN(b.started_at), MAX(b.completed_at)) AS production_minutes,
    o.due_date,
    CASE
        WHEN o.status = 'COMPLETED'
             AND (o.due_date IS NULL OR MAX(b.completed_at) IS NULL) THEN 'NOT_APPLICABLE'
        WHEN o.status = 'COMPLETED'
             AND DATE(MAX(b.completed_at)) <= o.due_date THEN 'ON_TIME'
        WHEN o.status = 'COMPLETED' THEN 'LATE'
        WHEN o.status IN ('PLANNED', 'RELEASED', 'IN_PROGRESS')
             AND o.due_date < CURDATE() THEN 'OVERDUE'
        ELSE 'NOT_APPLICABLE'
    END AS schedule_status
FROM production_orders o
JOIN products p            ON p.id = o.product_id
LEFT JOIN machines m       ON m.id = o.machine_id
LEFT JOIN production_batches b ON b.production_order_id = o.id
GROUP BY o.id, o.order_number, p.name, m.code, o.status,
         o.quantity_planned, o.quantity_completed, o.due_date, o.created_at
ORDER BY o.created_at DESC
LIMIT :limit;
