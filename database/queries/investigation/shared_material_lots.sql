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
-- Used by: rule R4 (shared material lot across the flagged batches)
-- Performance: EXPLAIN at demo volume (47 batch_materials rows, 9 lots, 35
--   batches) with four batch ids starts from production_batches as a range
--   scan on PRIMARY for the IN list (4 rows, "Using temporary; Using
--   filesort" for the GROUP BY and ORDER BY), reads batch_materials by ref on
--   its composite PRIMARY (batch_id leading, "Using index"), and material_lots
--   by eq_ref on PRIMARY. The correlated total_batches_using_lot subquery is a
--   DEPENDENT SUBQUERY on the implicit material_lot_id index (about 5 rows
--   per lot, "Using index"), executed once per lot in the result (3 lots in
--   the demo), not once per batch.
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
