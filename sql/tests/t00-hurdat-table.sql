SET ROLE prancer_write;
SET search_path = prancer, course, public;

SELECT count(*) FROM hurdat_tracks;

SELECT sum(num_track_points) FROM hurdat_storms;