"""Load 2024 Census ACS 5-year county demographics.

Requires CENSUS_API_KEY in local environment (never commit API keys to Git).
"""

import os
import requests

from course_db import connect

TEAM = "prancer"
# 2024 chosen because 2025 data has not been published yet
ACS_YEAR = 2024
URL = f"https://api.census.gov/data/{ACS_YEAR}/acs/acs5"
PARAMS = {
    "get": "NAME,B01003_001E,B19013_001E,B25077_001E,B25001_001E",
    "for": "county:*",
    "key": os.environ["CENSUS_API_KEY"],
}


def clean_num(val: str | None) -> float | None:
    """Convert a Census string value to float, returning None for blanks or negative missing codes (e.g. -666666666)."""
    if val is None or val == "":
        return None
    num = float(val)
    return None if num < 0 else num


# 1. Ask the Census Data API for all U.S. counties. raise_for_status() stops the
#    script here if the API answered with an error.
response = requests.get(URL, params=PARAMS, timeout=60)
response.raise_for_status()
data = response.json()

# 2. Turn the response into rows: one tuple per county matching course.counties,
#    in the order of the table's columns.
with connect(team=TEAM) as conn:
    valid_fips = {
        fips.strip()
        for (fips,) in conn.execute("SELECT county_fips FROM course.counties").fetchall()
    }

    rows = []
    for name, pop, inc, home, units, st, co in data[1:]:
        fips = f"{st.zfill(2)}{co.zfill(3)}"
        if fips not in valid_fips:
            continue
        pop_v = clean_num(pop)
        units_v = clean_num(units)
        rows.append((
            fips,
            name,
            ACS_YEAR,
            int(pop_v) if pop_v is not None else None,     # people (B01003_001E)
            clean_num(inc),                                # USD (B19013_001E)
            clean_num(home),                               # USD (B25077_001E)
            int(units_v) if units_v is not None else None, # housing units (B25001_001E)
        ))
    print(f"Read {len(rows)} matching counties from Census API.")

    # 3. Merge the rows, sending every value as a parameter. Nothing is saved until
    #    this block ends without an error.
    (before,) = conn.execute("SELECT count(*) FROM county_demographics").fetchone()
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO county_demographics (
              county_fips, county_name, acs_year, population,
              median_income, median_home_value, housing_units
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (county_fips)
            DO UPDATE SET county_name = EXCLUDED.county_name,
                          acs_year = EXCLUDED.acs_year,
                          population = EXCLUDED.population,
                          median_income = EXCLUDED.median_income,
                          median_home_value = EXCLUDED.median_home_value,
                          housing_units = EXCLUDED.housing_units
            """,
            rows,
        )
    (after,) = conn.execute("SELECT count(*) FROM county_demographics").fetchone()
    print(f"county_demographics had {before} rows and now has {after}.")
