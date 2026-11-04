-- Query 07: Production order completion summary
-- Business question: How many orders and units are planned versus completed,
--   broken down by product and status, with subtotals and a grand total?
-- Tables: production_orders, products
-- Techniques: GROUP BY ... WITH ROLLUP, GROUPING() to label subtotal rows,
--   NULLIF-guarded percentage. Grouping is by product code (unique), so two
--   products that happen to share a display name are not merged; the name is
--   carried with MAX() because it is constant within a code group.
-- Parameters: none
-- Result: one row per (product, status), one subtotal row per product, and a
--   grand-total row where product_code, product_name, and status read 'ALL'
-- Used by: analytics dashboard (order status chart), factory overview
-- Performance: single pass over production_orders; ix_production_orders_status
--   is not needed because every row is aggregated.
SELECT
    CASE WHEN GROUPING(p.code) = 1 THEN 'ALL' ELSE p.code END       AS product_code,
    CASE WHEN GROUPING(p.code) = 1 THEN 'ALL' ELSE MAX(p.name) END  AS product_name,
    CASE WHEN GROUPING(o.status) = 1 THEN 'ALL' ELSE o.status END   AS status,
    COUNT(o.id)                AS orders,
    SUM(o.quantity_planned)    AS planned_units,
    SUM(o.quantity_completed)  AS completed_units,
    ROUND(100 * SUM(o.quantity_completed) / NULLIF(SUM(o.quantity_planned), 0), 1) AS completion_pct
FROM production_orders o
JOIN products p ON p.id = o.product_id
GROUP BY p.code, o.status WITH ROLLUP;
