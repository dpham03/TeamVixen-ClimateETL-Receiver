from pathlib import Path

import pandas as pd
import requests

import io

from course_db import connect


# Configuration
BASE_URL = "https://www.ncei.noaa.gov/pub/data/ghcn/daily"

RAW_DIR = Path("data/raw/")

TARGET_STATES = {
    "TX", "LA", "AL", "GA",
    "FL", "SC", "NC", "VA"
}

ELEMENTS = {"PRCP", "TMAX", "TMIN"}







def get_stations():
  
    url = f"{BASE_URL}/ghcnd-stations.txt"

    response = requests.get(url, timeout=60)
    response.raise_for_status()

    stations = pd.read_fwf(
        io.StringIO(response.text),
        colspecs=[
            (0, 11),
            (12, 20),
            (21, 30),
            (31, 37),
            (38, 40),
            (41, 71)
        ],
        names=[
            "station_id", "lat", "lon",
            "elevation", "state", "name"
        ],
        dtype={"station_id": "string", "state": "string"}
    )

    stations = stations[
        stations["state"].isin(TARGET_STATES)
    ].copy()

    stations["elevation"] = stations["elevation"].replace(-999.9, pd.NA)

    return stations


def read_annual_file(year, station_ids):
    url = f"{BASE_URL}/by_year/{year}.csv.gz"

    response = requests.get(url, timeout=180)
    response.raise_for_status()

    columns = [
        "station_id", "date", "element", "value",
        "mflag", "qflag", "sflag", "obs_time"
    ]

    df = pd.read_csv(
        io.BytesIO(response.content),
        compression="gzip",
        header=None,
        names=columns,
        low_memory=False
    )

    df = df[df["station_id"].isin(station_ids)].copy()

    df = df[df["element"].isin(ELEMENTS)].copy()

    df = df[df["qflag"].isna()].copy()

    return df


def transform_ghcn(df):
    df = df.copy()

    # Convert dates (YYYYMMDD to datetime)
    df["date"] = pd.to_datetime(
        df["date"].astype(str),
        format="%Y%m%d",
        errors="coerce"
    )

    # Convert values to numeric
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["value"] = df["value"].replace(-9999, float("nan"))
    df["value"] = df["value"] / 10

    # Remove invalid records
    df = df.dropna(subset=["station_id", "date"])

    # Pivot to one row per station and date
    df = df.pivot(
    index=["station_id", "date"],
    columns="element",
    values="value"
    ).reset_index()

    # Rename columns to match PostgreSQL
    df = df.rename(columns={
        "TMAX": "tmax",
        "TMIN": "tmin",
        "PRCP": "precip"
    })

    # Ensure all expected columns exist
    for col in ["tmax", "tmin", "precip"]:
        if col not in df.columns:
            df[col] = pd.NA

    # Remove rows only if all three measurements are missing
    df = df.dropna(
        subset=["tmax", "tmin", "precip"],
        how="all"
    )

    # Select columns in database order
    df = df[
        ["station_id", "date", "tmax", "tmin", "precip"]
    ]

    return df


def load_stations(conn, stations):
    with conn.transaction():
        with conn.cursor() as cur:

            # Get state abbreviation -> FIPS mapping
            cur.execute("""
                SELECT state_abbr, state_fips
                FROM prancer.states
            """)

            state_fips = dict(cur.fetchall())

            df = stations.copy()
            df["state_fips"] = df["state"].map(state_fips)

            if df["state_fips"].isna().any():
                raise ValueError("Some stations have no matching state FIPS")

            # Convert missing elevation values to Python None
            df["elevation"] = df["elevation"].astype(object)
            df["elevation"] = df["elevation"].where(
                df["elevation"].notna(), None
            )

            rows = [
                (
                    row.station_id,
                    row.name,
                    row.state_fips,
                    row.lat,
                    row.lon,
                    row.elevation
                )
                for row in df.itertuples(index=False)
            ]

            cur.executemany("""
                INSERT INTO prancer.stations (
                    station_id, name, state_fips,
                    lat, lon, elevation
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (station_id)
                DO UPDATE SET
                    name = EXCLUDED.name,
                    state_fips = EXCLUDED.state_fips,
                    lat = EXCLUDED.lat,
                    lon = EXCLUDED.lon,
                    elevation = EXCLUDED.elevation
            """, rows)

    print(f"Processed {len(rows):,} stations")


def load_stage(conn, df):
    with conn.cursor() as cur:

        cur.execute("""
            CREATE TEMP TABLE IF NOT EXISTS stage_ghcn (
                station_id TEXT,
                date DATE,
                tmax DOUBLE PRECISION,
                tmin DOUBLE PRECISION,
                precip DOUBLE PRECISION
            ) ON COMMIT DROP
        """)

        buffer = io.StringIO()

        df.to_csv(
            buffer,
            index=False,
            na_rep=""
        )

        buffer.seek(0)

        with cur.copy("""
            COPY stage_ghcn (
                station_id, date, tmax, tmin, precip
            )
            FROM STDIN WITH (FORMAT CSV, HEADER TRUE)
        """) as copy:
            copy.write(buffer.getvalue())

    print(f"Loaded {len(df):,} rows into staging")


def merge_ghcn(conn):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO prancer.observations (
                station_id, date, tmax, tmin, precip
            )
            SELECT
                station_id,
                date,
                tmax,
                tmin,
                precip
            FROM stage_ghcn

            ON CONFLICT (station_id, date)
            DO UPDATE SET
                tmax = EXCLUDED.tmax,
                tmin = EXCLUDED.tmin,
                precip = EXCLUDED.precip

            WHERE (
                observations.tmax,
                observations.tmin,
                observations.precip
            ) IS DISTINCT FROM (
                EXCLUDED.tmax,
                EXCLUDED.tmin,
                EXCLUDED.precip
            )
        """)

        print(f"Inserted or updated {cur.rowcount:,} observations")
        

def refresh_ghcn(year=2025):

    # Load station metadata
    stations = get_stations()
    station_ids = set(stations["station_id"])

    print(f"Selected {len(station_ids):,} stations")

    # Extract and transform observations
    df = read_annual_file(year, station_ids)
    df = transform_ghcn(df)

    print(f"Transformed {len(df):,} station-date rows")

    # Load into PostgreSQL
    with connect(team="prancer", autocommit=True) as conn:
        with conn.transaction():
            load_stations(conn, stations)
            load_stage(conn, df)
            merge_ghcn(conn)

    print(f"Completed GHCN refresh for {year}")


if __name__ == "__main__":
    refresh_ghcn(2025)

