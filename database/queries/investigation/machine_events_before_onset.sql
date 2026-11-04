-- Investigation query: Machine events shortly before quality deteriorated
-- Business question: What happened to the machine in the hours before the
--   defect rate started to rise?
-- Tables: machine_events
-- Techniques: range scan on a composite index, INTERVAL arithmetic,
--   TIMESTAMPDIFF
-- Parameters: :machine_id, :onset_time (start of the onset hour), :lookback_hours
-- Result: events ordered most recent first with minutes_before_onset, which is
--   negative for an event inside the onset hour itself
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
