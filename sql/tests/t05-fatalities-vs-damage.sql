-- Sanity check for Q05; zero rows = pass.
-- Checks for negative death counts.

SELECT event_id
FROM prancer.storm_events
WHERE deaths_direct < 0
   OR deaths_indirect < 0;