"""Small nationwide GHCN API pilot, based on the class load_api.py pattern.

Put in src/ and run: python src/load_ghcn_nationwide_pilot.py
Start with 25 stations per state and one week before increasing coverage.
"""

import io

import pandas as pd
import requests
import time 

from course_db import connect

TEAM = "prancer"
API_URL = "https://www.ncei.noaa.gov/access/services/data/v1"
STATIONS_URL = "https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-stations.txt"

# Contiguous U.S. and DC (exclude Alaska and Hawaii).
STATES = [
    "AL", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "ID",
    "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI",
    "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY",
    "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN",
    "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC","AK", "HI"
]
START = "2025-09-01"
END = "2025-09-07"  # NOAA endDate is inclusive
STATIONS_PER_STATE = 25  # Increase gradually; use None for every station
BATCH_SIZE = 25
STOP_AT_GB = 6  # Soft safety limit for your whole team schema

SIZE_SQL = """
SELECT COALESCE(SUM(pg_total_relation_size(c.oid)), 0)
FROM pg_class AS c
JOIN pg_namespace AS n ON c.relnamespace = n.oid
WHERE n.nspname = %s AND c.relkind = 'r'
"""

response = requests.get(STATIONS_URL, timeout=60)
response.raise_for_status()

stations = pd.read_fwf(
    io.StringIO(response.text),
    colspecs=[(0, 11), (12, 20), (21, 30), (31, 37), (38, 40), (41, 71)],
    names=["station_id", "lat", "lon", "elevation", "state", "name"],
)
stations = stations[stations["state"].isin(STATES)].copy()
stations = stations.dropna(subset=["station_id", "name", "lat", "lon"])
if STATIONS_PER_STATE is not None:
    stations = stations.groupby("state", sort=False).head(STATIONS_PER_STATE)

print(f"Selected {len(stations)} stations across {stations['state'].nunique()} states/DC.")

# Read the state lookup once, as in your previous loader.
with connect(team=TEAM) as conn:
    state_fips = dict(conn.execute(
        "SELECT state_abbr, state_fips FROM prancer.states"
    ).fetchall())

# Every batch is committed separately, so the script can stop without losing
# previous batches and doesn't keep all NOAA results in memory.
for state, state_stations in stations.groupby("state", sort=True):
    station_ids = state_stations["station_id"].tolist()
    received = 0
    changed = 0

    for i in range(0, len(station_ids), BATCH_SIZE):
        batch_ids = station_ids[i:i + BATCH_SIZE]
        params = {
            "dataset": "daily-summaries",
            "stations": ",".join(batch_ids),
            "startDate": START,
            "endDate": END,
            "dataTypes": "TMAX,TMIN,PRCP",
            "units": "metric",
            "format": "json",
            }
        for attempt in range(3):
            try:
                response = requests.get(API_URL, params=params, timeout=60)
                response.raise_for_status()
                break
            except requests.exceptions.RequestException:
                if attempt == 2:
                    raise
                print(f"Request failed for {state}. Retrying...")
                time.sleep(5 * (attempt + 1))

        rows = []
        for obs in response.json():
            if not any(obs.get(k) not in (None, "") for k in ("TMAX", "TMIN", "PRCP")):
                continue
            rows.append((
                obs["STATION"], obs["DATE"],
                float(obs["TMAX"]) if obs.get("TMAX") not in (None, "") else None,
                float(obs["TMIN"]) if obs.get("TMIN") not in (None, "") else None,
                float(obs["PRCP"]) if obs.get("PRCP") not in (None, "") else None,
            ))
        received += len(rows)

        batch_stations = state_stations[
            state_stations["station_id"].isin(batch_ids)
        ]
        station_rows = [
            (
                s.station_id, s.name, state_fips[s.state],
                float(s.lat), float(s.lon),
                None if pd.isna(s.elevation) or s.elevation == -999.9 else float(s.elevation),
            )
            for s in batch_stations.itertuples(index=False)
        ]

        with connect(team=TEAM) as conn:
            with conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT INTO prancer.stations
                        (station_id, name, state_fips, lat, lon, elevation)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (station_id) DO NOTHING
                    """,
                    station_rows,
                )
                if rows:
                    cur.executemany(
                        """
                        INSERT INTO prancer.observations
                            (station_id, date, tmax, tmin, precip)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (station_id, date)
                        DO UPDATE SET
                            tmax = EXCLUDED.tmax,
                            tmin = EXCLUDED.tmin,
                            precip = EXCLUDED.precip
                        WHERE (prancer.observations.tmax,
                               prancer.observations.tmin,
                               prancer.observations.precip)
                              IS DISTINCT FROM
                              (EXCLUDED.tmax, EXCLUDED.tmin, EXCLUDED.precip)
                        """,
                        rows,
                    )
                    changed += cur.rowcount  # Inserts + updates; not unchanged rows

        # The batch has committed before we check the whole schema's size.
        with connect(team=TEAM) as conn:
            (bytes_used,) = conn.execute(SIZE_SQL, (TEAM,)).fetchone()

        gb_used = bytes_used / (1024 ** 3)
        print(f"{state}: {i + len(batch_ids)}/{len(station_ids)} stations; "
              f"{received} observations fetched; {changed} rows inserted/updated; "
              f"schema size {gb_used:.3f} GiB")

        if gb_used >= STOP_AT_GB:
            raise SystemExit(f"Stopped at {gb_used:.2f} GiB (safety limit {STOP_AT_GB} GiB).")

print("Nationwide pilot complete.")
