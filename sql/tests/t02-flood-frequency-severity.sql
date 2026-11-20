-- Sanity check for Q02; zero rows = pass.
-- Checks for negative flood property damage.

SELECT event_id
FROM prancer.storm_events
WHERE event_type IN ('Flood', 'Flash Flood')
  AND state_fips IN ('48', '22', '12', '13', '45', '37')
  AND damage_property_usd < 0;