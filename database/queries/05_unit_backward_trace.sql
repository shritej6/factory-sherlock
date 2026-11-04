-- Query 05: Unit backward traceability
-- Business question: Given a serial number, which batch, machine, order,
--   product, and material lots does it come from, and what did inspection find?
-- Tables: production_units, production_batches, machines, production_orders,
--   products, batch_materials, material_lots, inspections, product_specifications
-- Techniques: join chain from child to ancestors, correlated subquery with
--   GROUP_CONCAT to fold inspection results into one column
-- Parameters: :serial_number
-- Result: one row per material lot used by the unit's batch (all other
--   columns repeat); inspection_summary lists each characteristic's result
-- Used by: traceability screen (backward)
-- Known limit: GROUP_CONCAT output is cut at group_concat_max_len, which
--   defaults to 1024 characters; a unit with more than roughly 25
--   characteristics would need the session variable raised.
-- Performance: production_units.serial_number is UNIQUE; the correlated
--   subquery runs once per output row against uq_inspection_unit_spec.
SELECT
    u.serial_number,
    u.produced_at,
    b.batch_number,
    b.status   AS batch_status,
    m.code     AS machine_code,
    m.name     AS machine_name,
    o.order_number,
    p.code     AS product_code,
    p.name     AS product_name,
    ml.lot_number,
    ml.material_name,
    ml.supplier,
    ml.status  AS lot_status,
    (
        SELECT GROUP_CONCAT(
                   CONCAT(ps.characteristic, '=', i.measured_value, ' ', i.result)
                   ORDER BY ps.characteristic SEPARATOR '; ')
        FROM inspections i
        JOIN product_specifications ps ON ps.id = i.specification_id
        WHERE i.unit_id = u.id
    ) AS inspection_summary
FROM production_units u
JOIN production_batches b ON b.id = u.batch_id
JOIN machines           m ON m.id = b.machine_id
JOIN production_orders  o ON o.id = b.production_order_id
JOIN products           p ON p.id = o.product_id
LEFT JOIN batch_materials bm ON bm.batch_id = b.id
LEFT JOIN material_lots   ml ON ml.id = bm.material_lot_id
WHERE u.serial_number = :serial_number
ORDER BY ml.lot_number;
