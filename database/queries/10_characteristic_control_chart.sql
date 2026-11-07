-- Query 10: Per-characteristic control chart (X-bar and S by batch)
-- Business question: For one measured characteristic, how did the batch mean
--   and the within-batch spread move over a time window, and which batches fall
--   outside the three-sigma control limits computed from that window?
-- Tables: inspections, production_units, production_batches, machines,
--   product_specifications
-- Techniques: three chained CTEs (filter, per-subgroup aggregation, window
--   functions over the whole window); subgroup = production batch; STDDEV_SAMP
--   and VAR_SAMP (both NULL when a subgroup has one sample); window functions
--   SUM OVER () and AVG OVER () so the control limits are computed once over
--   every subgroup and repeated on each row; the optional machine filter
--   (:machine_id IS NULL OR b.machine_id = :machine_id) as in query 08; the
--   specification row is joined by constant for the reference columns.
-- Formula (stated once here and in docs/database/queries.md):
--   grand_mean      = SUM(measured_value) / COUNT(*) over every inspection in
--                     the window (the sample-size-weighted mean of the subgroup
--                     means)
--   pooled_std_dev  = SQRT( SUM((n_i - 1) * s_i^2) / SUM(n_i - 1) ) over the
--                     subgroups with n_i >= 2, where n_i is the subgroup sample
--                     count and s_i its STDDEV_SAMP
--   avg_sample_size = AVG(n_i) over every subgroup
--   ucl / lcl       = grand_mean +/- 3 * pooled_std_dev / SQRT(avg_sample_size)
--   No c4 bias correction is applied, and no S-chart limits (B3/B4) are
--   computed: std_dev is returned per subgroup for plotting only. When every
--   subgroup has a single sample, pooled_std_dev, ucl, and lcl are NULL.
-- Parameters: :specification_id (required), :window_start, :window_end
--   (DATETIME, half-open on inspected_at), :machine_id (NULL for all machines)
-- Result: one row per batch with at least one inspection of the specification
--   inside the window, ordered by subgroup_start then batch_id: batch_id,
--   batch_number, machine_code, subgroup_start (batch started_at),
--   sample_count, mean_value, std_dev, min_value, max_value, target_value,
--   lower_spec_limit, upper_spec_limit, grand_mean, ucl, lcl. mean_value,
--   std_dev, grand_mean, ucl, and lcl are rounded to four places; the other
--   numeric columns are exact DECIMAL(10,3) values. A batch whose inspections
--   straddle a window edge contributes only the inspections inside the window.
-- Used by: analytics dashboard (control chart screen), SQL explorer
-- Performance: EXPLAIN at demo volume (1,400 inspections, 240 of them for the
--   chosen specification, all inside the four-day window) with :machine_id =
--   NULL reads inspections by ref on the specification_id foreign-key index
--   (240 rows, time predicate applied as "Using where"), then units, batches,
--   and machines by eq_ref on their primary keys, and the specification row as
--   const. ix_inspections_time_result is in possible_keys but not chosen while
--   the window covers most of the table; it is still listed with a one-hour
--   window (240 inspections per hour across all specifications, so neither
--   predicate is more selective), and with a ten-minute window the optimizer
--   switches to a range scan on ix_inspections_time_result (42 rows, "Using
--   index condition") and applies the specification filter as "Using where".
--   That is the production case, where the window is small relative to
--   history. With :machine_id = 3 the plan starts from machines (const) and
--   production_batches by ref on ix_production_batches_machine_time (12 rows,
--   "Using index condition"), units by ref on uq_unit_batch_sequence (covering),
--   and inspections by eq_ref on uq_inspection_unit_spec with the time filter
--   as "Using where". In every variant there is one temporary table for the
--   GROUP BY, the window functions run over the small subgroup set (12 rows
--   here, at most one per batch), and the final ORDER BY is a filesort.
WITH window_inspections AS (
    SELECT
        b.id           AS batch_id,
        b.batch_number,
        m.code         AS machine_code,
        b.started_at   AS subgroup_start,
        i.measured_value
    FROM inspections i
    JOIN production_units   u ON u.id = i.unit_id
    JOIN production_batches b ON b.id = u.batch_id
    JOIN machines           m ON m.id = b.machine_id
    WHERE i.specification_id = :specification_id
      AND i.inspected_at >= :window_start
      AND i.inspected_at <  :window_end
      AND (:machine_id IS NULL OR b.machine_id = :machine_id)
),
subgroups AS (
    SELECT
        batch_id,
        batch_number,
        machine_code,
        subgroup_start,
        COUNT(*)                    AS sample_count,
        SUM(measured_value)         AS sum_value,
        AVG(measured_value)         AS mean_value,
        VAR_SAMP(measured_value)    AS var_sample,
        STDDEV_SAMP(measured_value) AS std_dev,
        MIN(measured_value)         AS min_value,
        MAX(measured_value)         AS max_value
    FROM window_inspections
    GROUP BY batch_id, batch_number, machine_code, subgroup_start
),
limits AS (
    SELECT
        sg.*,
        SUM(sg.sum_value) OVER () / SUM(sg.sample_count) OVER ()          AS grand_mean,
        SQRT(SUM((sg.sample_count - 1) * sg.var_sample) OVER ()
             / NULLIF(SUM(sg.sample_count - 1) OVER (), 0))                AS pooled_std_dev,
        AVG(sg.sample_count) OVER ()                                       AS avg_sample_size
    FROM subgroups sg
)
SELECT
    l.batch_id,
    l.batch_number,
    l.machine_code,
    l.subgroup_start,
    l.sample_count,
    ROUND(l.mean_value, 4)          AS mean_value,
    ROUND(l.std_dev, 4)             AS std_dev,
    l.min_value,
    l.max_value,
    s.target_value,
    s.target_value - s.tolerance    AS lower_spec_limit,
    s.target_value + s.tolerance    AS upper_spec_limit,
    ROUND(l.grand_mean, 4)          AS grand_mean,
    ROUND(l.grand_mean + 3 * l.pooled_std_dev / SQRT(l.avg_sample_size), 4) AS ucl,
    ROUND(l.grand_mean - 3 * l.pooled_std_dev / SQRT(l.avg_sample_size), 4) AS lcl
FROM limits l
JOIN product_specifications s ON s.id = :specification_id
ORDER BY l.subgroup_start, l.batch_id;
