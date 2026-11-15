"""Download NHC HURDAT2, normalize into two CSVs and load via COPY."""

import csv
from datetime import datetime, timezone
from pathlib import Path
import re
from urllib.parse import urljoin


import requests

from course_db import connect

TEAM = "prancer"
INDEX_URL = "https://www.nhc.noaa.gov/data/hurdat/"
HEADERS = {"User-Agent": "36-614 project (ahou@andrew.cmu.edu)"}
RAW_TXT = Path("data/raw/hurdat2.txt")
STORMS_CSV = Path("data/raw/hurdat_storms.csv")
TRACKS_CSV = Path("data/raw/hurdat_tracks.csv")
MIN_YEAR = 1980  # Modern satellite era (1979+ has complete central pressure & satellite coverage)

# 1. Find and download the latest Atlantic HURDAT2 file into data/raw/
RAW_TXT.parent.mkdir(parents=True, exist_ok=True)
index_resp = requests.get(INDEX_URL, headers=HEADERS, timeout=30)
index_resp.raise_for_status()
matches = re.findall(r'href="([^"]*hurdat2-1851-[^"]+\.txt)"', index_resp.text, flags=re.IGNORECASE)
file_url = urljoin(INDEX_URL, sorted(matches)[-1])
print(f"Downloading {file_url}...")

resp = requests.get(file_url, headers=HEADERS, timeout=60)
resp.raise_for_status()
if resp.text.lstrip().startswith("<"):
        raise SystemExit(f"Expected plain-text HURDAT2 data, got HTML from {file_url}")
RAW_TXT.write_text(resp.text, encoding="utf-8")

# 2. Parse alternating storm headers (4 fields) and track fixes (20 or 21 fields)
#    and validate that every storm's track count matches its declared header count.
storms_out = []
tracks_out = []
current_id = None
expected_pts = 0
seen_pts = 0
keep_storm = False

for line_num, raw_line in enumerate(RAW_TXT.read_text(encoding="utf-8").splitlines(), start=1):
    if not raw_line.strip():
        continue
    parts = [p.strip() for p in raw_line.split(",")]

    # Header line format: AL092021, IDA, 40,
    if len(parts) == 4:
        storm_id, storm_name, n_pts_str, _ = parts
        if storm_id[:2] in ("AL", "EP", "CP"):
            if current_id is not None and seen_pts != expected_pts:
                raise ValueError(f"Line {line_num}: {current_id} declared {expected_pts} pts, found {seen_pts}")
            current_id = storm_id
            expected_pts = int(n_pts_str)
            seen_pts = 0
            year = int(storm_id[4:8])
            keep_storm = year >= MIN_YEAR
            if keep_storm:
                storms_out.append([
                    storm_id,
                    storm_name,
                    storm_id[:2],
                    int(storm_id[2:4]),
                    year,
                    expected_pts,
                ])
    # Header line format (20 or 21 fields depending on pre/post-2021 RMW column)
    elif len(parts) in (20, 21):
        seen_pts += 1
        if not keep_storm:
            continue
        ymd, hm, rec_id, status, lat_s, lon_s, wind_s, pres_s = parts[:8]
        rec_id = rec_id or "R"  # 'R' = regular synoptic point (non-empty for CSV COPY)
        dt = datetime.strptime(ymd + hm.zfill(4), "%Y%m%d%H%M").replace(tzinfo=timezone.utc).isoformat()
        lat = float(lat_s[:-1]) * (-1 if lat_s.endswith("S") else 1)  # decimal degrees
        lon = float(lon_s[:-1]) * (-1 if lon_s.endswith("W") else 1)  # decimal degrees
        wind = int(wind_s) if int(wind_s) >= 0 else ""                 # knots (-99 -> NULL)
        pres = int(pres_s) if int(pres_s) > 0 else ""                  # millibars (-999 -> NULL)
        tracks_out.append([current_id, dt, rec_id, status, lat, lon, wind, pres])

    else:
        raise ValueError(f"Line {line_num}: unexpected field count ({len(parts)}): {raw_line!r}")
    
if current_id is not None and seen_pts != expected_pts:
    raise ValueError(f"EOF: {current_id} declared {expected_pts} pts, found {seen_pts}")

with open(STORMS_CSV, "w", encoding="utf-8", newline="") as sf:
    sw = csv.writer(sf)
    sw.writerow(["storm_id", "storm_name", "basin", "cyclone_number", "season_year", "num_track_points"])
    sw.writerows(storms_out)

with open(TRACKS_CSV, "w", encoding="utf-8", newline="") as tf:
    tw = csv.writer(tf)
    tw.writerow(["storm_id", "observed_at", "record_identifier", "system_status", "lat", "lon", "max_wind_kt", "min_pressure_mb"])
    tw.writerows(tracks_out)

# 3. Load both normalized CSVs via COPY (exact starter load_csv.py pattern)
with connect(team=TEAM) as conn:
    with conn.cursor() as cur:
        with cur.copy(
            "COPY hurdat_storms (storm_id, storm_name, basin, cyclone_number, season_year, num_track_points) "
            "FROM STDIN (FORMAT csv, HEADER true)"
        ) as copy:
            with open(STORMS_CSV, "rb") as f:
                for line in f:
                    copy.write(line)
        print(f"Loaded {cur.rowcount} rows from {STORMS_CSV}.")

        with cur.copy(
            "COPY hurdat_tracks (storm_id, observed_at, record_identifier, system_status, lat, lon, max_wind_kt, min_pressure_mb) "
            "FROM STDIN (FORMAT csv, HEADER true)"
        ) as copy:
            with open(TRACKS_CSV, "rb") as f:
                for line in f:
                    copy.write(line)
        print(f"Loaded {cur.rowcount} rows from {TRACKS_CSV}.")
