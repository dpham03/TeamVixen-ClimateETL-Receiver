-- Sanity check for Q06; zero rows = pass.
-- Checks for negative county populations.

SELECT county_fips
FROM prancer.county_demographics
WHERE population < 0;
