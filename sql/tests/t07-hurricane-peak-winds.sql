-- Sanity check for Q07; zero rows = pass.
-- Checks for negative wind speeds.

SELECT track_id
FROM prancer.hurdat_tracks
WHERE max_wind_kt < 0;
