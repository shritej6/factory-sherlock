-- Query 03: Recurring defect categories by machine
-- Business question: Which defect categories recur on each machine in a window,
--   and what share of that machine's defects does each category represent?
-- Tables: inspection_defects, inspections, defect_types, production_units,
--   production_batches, machines
-- Techniques: CTE, five-table join through two junction/bridge tables,
--   window functions with PARTITION BY (SUM OVER, DENSE_RANK OVER),
--   optional parameter pattern (:machine_id IS NULL OR ...)
-- Parameters: :window_start, :window_end, :machine_id (NULL for all machines)
-- Result: one row per (machine, defect type) with occurrences, machine_total,
--   share_of_machine_defects, rank_within_machine
-- Used by: analytics dashboard, investigation rule R2 (dominant defect)
-- Performance: EXPLAIN at demo volume with :machine_id = 3: machines is
--   resolved as const; inspection_defects is read with an index scan of its
--   defect_type_id index (51 rows, Using index); defect_types, inspections,
--   production_units, and production_batches are each reached by eq_ref on
--   their primary key, with the time window applied as "Using where" on
--   inspections and the machine filter as "Using where" on batches.
--   ix_inspections_time_result is in possible_keys but not used. One
--   temporary table for the GROUP BY and one filesort for the window
--   ordering over the small CTE output.
WITH defect_counts AS (
    SELECT
        m.id   AS machine_id,
        m.code AS machine_code,
        d.code AS defect_code,
        d.name AS defect_name,
        COUNT(*) AS occurrences
    FROM inspection_defects idf
    JOIN inspections       i ON i.id = idf.inspection_id
    JOIN defect_types      d ON d.id = idf.defect_type_id
    JOIN production_units  u ON u.id = i.unit_id
    JOIN production_batches b ON b.id = u.batch_id
    JOIN machines          m ON m.id = b.machine_id
    WHERE i.inspected_at >= :window_start
      AND i.inspected_at <  :window_end
      AND (:machine_id IS NULL OR m.id = :machine_id)
    GROUP BY m.id, m.code, d.code, d.name
)
SELECT
    machine_id,
    machine_code,
    defect_code,
    defect_name,
    occurrences,
    SUM(occurrences) OVER (PARTITION BY machine_code)                            AS machine_total,
    ROUND(occurrences / SUM(occurrences) OVER (PARTITION BY machine_code), 4)   AS share_of_machine_defects,
    DENSE_RANK() OVER (PARTITION BY machine_code ORDER BY occurrences DESC)      AS rank_within_machine
FROM defect_counts
ORDER BY machine_code, rank_within_machine, defect_code;
