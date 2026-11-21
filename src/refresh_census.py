import argparse
import os
import time
import requests

from course_db import connect


# Configuration
BASE_URL = "https://api.census.gov/data"

TARGET_STATE_FIPS = {
    "01",  # Alabama
    "12",  # Florida
    "13",  # Georgia
    "22",  # Louisiana
    "37",  # North Carolina
    "45",  # South Carolina
    "48",  # Texas
    "51"   # Virginia
}

DEFAULT_ACS_YEAR = 2024


def clean_value(value):

    if value is None or value == "":
        return None

    value = int(value)

    if value < 0:
        return None

    return value


def fetch_census_data(acs_year):

    # have to go to this link 
    # https://api.census.gov/data/key_signup.html
    # to get API KEY and run this line 

    # export CENSUS_API_KEY="YOUR API KEY HERE"

    api_key = os.environ.get("CENSUS_API_KEY")

    if not api_key:
        raise ValueError("Missing CENSUS_API_KEY environment variable")

    url = f"{BASE_URL}/{acs_year}/acs/acs5"

    params = {
        "get": "NAME,B01003_001E,B19013_001E,B25077_001E,B25001_001E",
        "for": "county:*",
        "key": api_key
    }

    print(f"Fetching {acs_year} ACS 5-year estimates")

    for attempt in range(5):

        try:
            response = requests.get(
                url,
                params=params,
                timeout=60
            )

            response.raise_for_status()
            break

        except requests.exceptions.RequestException:

            if attempt == 4:
                raise

            print("Census request failed. Retrying...")
            time.sleep(5)

    rows = []

    for name, pop, income, home, units, state, county in response.json()[1:]:

        if state not in TARGET_STATE_FIPS:
            continue

        county_fips = state.zfill(2) + county.zfill(3)

        rows.append((
            county_fips,
            name,
            acs_year,
            clean_value(pop),
            clean_value(income),
            clean_value(home),
            clean_value(units)
        ))

    print(f"Fetched {len(rows):,} counties")

    return rows


def load_stage(conn, rows):

    with conn.cursor() as cur:

        cur.execute("""
            CREATE TEMP TABLE stage_census (
                county_fips CHAR(5),
                county_name TEXT,
                acs_year INTEGER,
                population INTEGER,
                median_income NUMERIC(12, 2),
                median_home_value NUMERIC(14, 2),
                housing_units INTEGER
            ) ON COMMIT DROP
        """)

        with cur.copy("""
            COPY stage_census (
                county_fips,
                county_name,
                acs_year,
                population,
                median_income,
                median_home_value,
                housing_units
            )
            FROM STDIN
        """) as copy:

            for row in rows:
                copy.write_row(row)


def validate(conn):

    checks = {

        "Duplicate county FIPS": """
            SELECT COUNT(*)
            FROM (
                SELECT county_fips
                FROM stage_census
                GROUP BY county_fips
                HAVING COUNT(*) > 1
            ) AS duplicates
        """,

        "Invalid county FIPS": """
            SELECT COUNT(*)
            FROM stage_census
            WHERE county_fips IS NULL
               OR county_fips !~ '^[0-9]{5}$'
        """,

        "Unknown county FIPS": """
            SELECT COUNT(*)
            FROM stage_census AS s
            WHERE NOT EXISTS (
                SELECT 1
                FROM course.counties AS c
                WHERE c.county_fips = s.county_fips
            )
        """,

        "Missing required values": """
            SELECT COUNT(*)
            FROM stage_census
            WHERE county_name IS NULL
               OR acs_year IS NULL
        """,

        "Invalid ACS year": """
            SELECT COUNT(*)
            FROM stage_census
            WHERE acs_year NOT BETWEEN 2009 AND 2030
        """,

        "Negative demographic values": """
            SELECT COUNT(*)
            FROM stage_census
            WHERE population < 0
               OR median_income < 0
               OR median_home_value < 0
               OR housing_units < 0
        """
    }

    with conn.cursor() as cur:

        for name, query in checks.items():

            cur.execute(query)
            count = cur.fetchone()[0]

            if count:
                raise ValueError(
                    f"{name}: {count:,} invalid rows"
                )


def merge_census(conn):

    with conn.cursor() as cur:

        # Count new counties
        cur.execute("""
            SELECT COUNT(*)
            FROM stage_census AS s
            WHERE NOT EXISTS (
                SELECT 1
                FROM prancer.county_demographics AS d
                WHERE d.county_fips = s.county_fips
            )
        """)

        inserted = cur.fetchone()[0]

        # Insert new counties and update changed demographics
        cur.execute("""
            INSERT INTO prancer.county_demographics (
                county_fips,
                county_name,
                acs_year,
                population,
                median_income,
                median_home_value,
                housing_units
            )
            SELECT
                county_fips,
                county_name,
                acs_year,
                population,
                median_income,
                median_home_value,
                housing_units
            FROM stage_census

            ON CONFLICT (county_fips)
            DO UPDATE SET
                county_name = EXCLUDED.county_name,
                acs_year = EXCLUDED.acs_year,
                population = EXCLUDED.population,
                median_income = EXCLUDED.median_income,
                median_home_value = EXCLUDED.median_home_value,
                housing_units = EXCLUDED.housing_units

            WHERE EXCLUDED.acs_year >= county_demographics.acs_year
              AND (
                county_demographics.county_name,
                county_demographics.acs_year,
                county_demographics.population,
                county_demographics.median_income,
                county_demographics.median_home_value,
                county_demographics.housing_units
            ) IS DISTINCT FROM (
                EXCLUDED.county_name,
                EXCLUDED.acs_year,
                EXCLUDED.population,
                EXCLUDED.median_income,
                EXCLUDED.median_home_value,
                EXCLUDED.housing_units
            )
        """)

        changed = cur.rowcount
        updated = changed - inserted

        return inserted, updated


def record_success(conn, staged, inserted, updated):

    conn.execute("""
        INSERT INTO prancer.ingestion_runs (
            source,
            status,
            rows_staged,
            rows_inserted,
            rows_updated
        )
        VALUES (%s, %s, %s, %s, %s)
    """, (
        "census",
        "success",
        staged,
        inserted,
        updated
    ))


def refresh_census(acs_year=DEFAULT_ACS_YEAR):

    if not 2009 <= acs_year <= 2030:
        raise ValueError("Invalid ACS year")

    rows = fetch_census_data(acs_year)

    if not rows:
        raise ValueError("No Census records returned")

    with connect(team="prancer", autocommit=True) as conn:

        with conn.transaction():

            load_stage(conn, rows)

            validate(conn)

            inserted, updated = merge_census(conn)

            record_success(
                conn,
                len(rows),
                inserted,
                updated
            )

    print(
        f"Census refresh complete.\n"
        f"ACS year: {acs_year}\n"
        f"Rows staged: {len(rows):,}\n"
        f"Rows inserted: {inserted:,}\n"
        f"Rows updated: {updated:,}\n"
        f"Rows unchanged/skipped: {len(rows) - inserted - updated:,}"
    )


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--acs-year",
        type=int,
        default=DEFAULT_ACS_YEAR
    )

    args = parser.parse_args()

    refresh_census(args.acs_year)