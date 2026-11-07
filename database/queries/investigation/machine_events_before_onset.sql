-- Investigation query: Machine events shortly before quality deteriorated
-- Business question: What happened to the machine in the hours before the
--   defect rate started to rise?
-- Tables: machine_events
-- Techniques: range scan on a composite index, INTERVAL arithmetic,
--   TIMESTAMPDIFF
-- Parameters: :machine_id, :onset_time (start of the onset hour), :lookback_hours
-- Result: events ordered most recent first with minutes_before_onset, which is
--   negative for an event inside the onset hour itself
-- Used by: rule R3 (events before the detected onset hour)
-- Performance: EXPLAIN at demo volume (12 machine_events rows, 3 of them for
--   CNC-03) is a full scan with "Using where; Using filesort";
--   ix_machine_events_machine_time (machine_id, occurred_at) is in
--   possible_keys but a 12-row table is cheaper to scan than to seek. With 72
--   events (23 for the machine, measured on a database grown with extra
--   simulation runs) the optimizer switches to a range scan on that index
--   (machine_id = const, occurred_at between the two bounds; 3 rows, "Using
--   index condition; Using where; Backward index scan"), which also delivers
--   the ORDER BY occurred_at DESC without a filesort; the event_type <>
--   'STATE_CHANGE' filter is applied as "Using where". The result is a
--   handful of rows (one TOOL_WEAR event in the demo).
SELECT
    e.id AS event_id,
    e.event_type,
    e.severity,
    e.description,
    e.occurred_at,
    TIMESTAMPDIFF(MINUTE, e.occurred_at, :onset_time) AS minutes_before_onset
FROM machine_events e
WHERE e.machine_id = :machine_id
  AND e.event_type <> 'STATE_CHANGE'
  AND e.occurred_at >= :onset_time - INTERVAL :lookback_hours HOUR
  AND e.occurred_at < :onset_time + INTERVAL 1 HOUR
ORDER BY e.occurred_at DESC;
