-- Query 04: Material lot forward traceability
-- Business question: Given a material lot, which batches consumed it, on which
--   machines and orders, and how many of the resulting units failed inspection?
-- Tables: material_lots, batch_materials (junction), production_batches,
--   machines, production_orders, products, production_units, inspections
-- Techniques: many-to-many traversal through a junction table, eight-table
--   join, COUNT(DISTINCT), conditional COUNT with CASE
-- Parameters: :lot_number
-- Result: one row per batch that used the lot
-- Used by: traceability service (forward trace); rule R6 uses investigation/shared_material_lots.sql
-- Performance: material_lots.lot_number is UNIQUE so the driving row is found
--   by index; batch_materials is read via its primary key prefix.
SELECT
    ml.lot_number,
    ml.material_name,
    ml.supplier,
    ml.status        AS lot_status,
    b.id             AS batch_id,
    b.batch_number,
    b.status         AS batch_status,
    b.started_at,
    m.code           AS machine_code,
    o.order_number,
    p.name           AS product_name,
    bm.quantity_used,
    COUNT(DISTINCT u.id) AS units_produced,
    COUNT(DISTINCT CASE WHEN i.result = 'FAIL' THEN i.unit_id END) AS units_failed
FROM material_lots ml
JOIN batch_materials    bm ON bm.material_lot_id = ml.id
JOIN production_batches b  ON b.id = bm.batch_id
JOIN machines           m  ON m.id = b.machine_id
JOIN production_orders  o  ON o.id = b.production_order_id
JOIN products           p  ON p.id = o.product_id
LEFT JOIN production_units u ON u.batch_id = b.id
LEFT JOIN inspections      i ON i.unit_id = u.id
WHERE ml.lot_number = :lot_number
GROUP BY ml.id, ml.lot_number, ml.material_name, ml.supplier, ml.status,
         b.id, b.batch_number, b.status, b.started_at, m.code, o.order_number,
         p.name, bm.quantity_used
ORDER BY b.started_at;
