-- Sanity check for Q04; zero rows = pass.
-- Checks for negative event property damage.

SELECT episode_id
FROM prancer.storm_events
WHERE episode_id IS NOT NULL
  AND damage_property_usd < 0;