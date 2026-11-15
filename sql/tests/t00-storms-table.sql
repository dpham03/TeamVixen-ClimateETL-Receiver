SET ROLE prancer_write;
SET search_path = prancer, course, public;

-- AI Checklist #5

-- Trace one record end to end: NOAA 1997 Kansas hail record
-- EVENT_ID = 5600491
-- raw CSV had STATE_FIPS=20, CZ_TYPE='C', CZ_FIPS=077, BEGIN_LAT=97.1 (bad), BEGIN_LON=-97.38
-- expected in table: county_fips='20077', fips_source='direct', begin_lat IS NULL, begin_lon=-97.38
SELECT
    event_id, 
    episode_id, 
    state_abbr, 
    county_fips, 
    fips_source, 
    event_type, 
    begin_ts, 
    magnitude, 
    begin_lat, 
    begin_lon
FROM storm_events
WHERE event_id = 5600491;
