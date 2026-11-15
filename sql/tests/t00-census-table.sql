SET ROLE prancer_write;
SET search_path = prancer, course, public;

SELECT *
FROM county_demographics
WHERE population < 0 OR population IS NULL
LIMIT 5;

SELECT *
FROM county_demographics
WHERE median_income < 0 OR median_income IS NULL
LIMIT 5;

SELECT *
FROM county_demographics
WHERE median_home_value < 0 OR median_home_value IS NULL
LIMIT 5;

SELECT *
FROM county_demographics
WHERE housing_units < 0 OR housing_units IS NULL
LIMIT 5;