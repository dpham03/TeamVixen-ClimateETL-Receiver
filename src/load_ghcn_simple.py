"""Simple GHCN-Daily API loader, based on the course's load_api.py example.

Run from the repository root:
    python src/load_ghcn_api_simple.py

Change STATES, START, END, and STATIONS_PER_STATE below to change the scope.
Set STATIONS_PER_STATE = None to request all listed stations in those states.
"""

import io
import pandas as pd
import requests

from course_db import connect

TEAM = "prancer"
URL = "https://www.ncei.noaa.gov/access/services/data/v1"
STATIONS_URL = "https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-stations.txt"

# Start small to test the API and database merge.
STATES = ["TX", "LA", "FL", "GA", "SC", "NC"]
START = "2025-09-01"
END = "2025-09-07"                # NOAA endDate is inclusive
STATIONS_PER_STATE = 3           # Set to None for every listed station
BATCH_SIZE = 10

# 1. Read NOAA's station list. It is a fixed-width text file.
response = requests.get(STATIONS_URL, timeout=60)
response.raise_for_status()

stations = pd.read_fwf(
    io.StringIO(response.text),
    colspecs=[(0, 11), (12, 20), (21, 30), (31, 37), (38, 40), (41, 71)],
    names=["station_id", "lat", "lon", "elevation", "state", "name"],
)
stations = stations[stations["state"].isin(STATES)].copy()

if STATIONS_PER_STATE is not None:
    stations = stations.groupby("state", sort=False).head(STATIONS_PER_STATE)

stations = stations.dropna(subset=["station_id", "name", "lat", "lon"])
print(f"Selected {len(stations)} stations.")

# 2. Ask NOAA for daily observations, a few stations per API call.
rows = []
station_ids = stations["station_id"].tolist()

for i in range(0, len(station_ids), BATCH_SIZE):
    batch = station_ids[i:i + BATCH_SIZE]
    params = {
        "dataset": "daily-summaries",
        "stations": ",".join(batch),
        "startDate": START,
        "endDate": END,
        "dataTypes": "TMAX,TMIN,PRCP",
        "units": "metric",
        "format": "json",
    }

    response = requests.get(URL, params=params, timeout=60)
    response.raise_for_status()

    for obs in response.json():
        # The API may omit a measurement if it is unavailable that day.
        if not any(obs.get(x) not in (None, "") for x in ("TMAX", "TMIN", "PRCP")):
            continue
        rows.append((
            obs["STATION"],
            obs["DATE"],
            float(obs["TMAX"]) if obs.get("TMAX") not in (None, "") else None,
            float(obs["TMIN"]) if obs.get("TMIN") not in (None, "") else None,
            float(obs["PRCP"]) if obs.get("PRCP") not in (None, "") else None,
        ))

print(f"Read {len(rows)} daily observations from NOAA's API.")

# 3. Merge station metadata and observations into PostgreSQL.
#    One connection transaction: if an INSERT fails, neither table is partially saved.
with connect(team=TEAM) as conn:
    state_fips = dict(conn.execute(
        "SELECT state_abbr, state_fips FROM prancer.states"
    ).fetchall())

    station_rows = [
        (
            s.station_id,
            s.name,
            state_fips[s.state],
            float(s.lat),
            float(s.lon),
            None if pd.isna(s.elevation) or s.elevation == -999.9 else float(s.elevation),
        )
        for s in stations.itertuples(index=False)
    ]

    (before,) = conn.execute("SELECT count(*) FROM prancer.observations").fetchone()

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
            """,
            rows,
        )

    (after,) = conn.execute("SELECT count(*) FROM prancer.observations").fetchone()
    print(f"observations had {before} rows and now has {after}.")