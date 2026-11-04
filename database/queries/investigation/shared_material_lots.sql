-- Investigation query: Material lots used by the affected batches
-- Business question: Do the affected batches share a material lot, and how
--   widely was that lot used elsewhere?
-- Tables: material_lots, batch_materials (junction), production_batches
-- Techniques: expanding IN parameter, COUNT(DISTINCT), GROUP_CONCAT,
--   correlated scalar subquery for the lot's total usage
-- Parameters: :batch_ids (list of batch ids)
-- Result: one row per lot; affected_batches_using_lot > 1 means the lot is
--   shared across the flagged batches
-- Known limit: batch_numbers is a GROUP_CONCAT and is cut at
--   group_concat_max_len (default 1024 characters, about 40 batch numbers);
--   affected_batches_using_lot stays exact because it is a COUNT.
SELECT
    ml.id   AS lot_id,
    ml.lot_number,
    ml.material_name,
    ml.supplier,
    ml.status AS lot_status,
    COUNT(DISTINCT bm.batch_id) AS affected_batches_using_lot,
    GROUP_CONCAT(DISTINCT b.batch_number ORDER BY b.batch_number SEPARATOR ', ') AS batch_numbers,
    (
        SELECT COUNT(*) FROM batch_materials bm2 WHERE bm2.material_lot_id = ml.id
    ) AS total_batches_using_lot
FROM material_lots ml
JOIN batch_materials    bm ON bm.material_lot_id = ml.id
JOIN production_batches b  ON b.id = bm.batch_id
WHERE bm.batch_id IN :batch_ids
GROUP BY ml.id, ml.lot_number, ml.material_name, ml.supplier, ml.status
ORDER BY affected_batches_using_lot DESC, ml.lot_number;
