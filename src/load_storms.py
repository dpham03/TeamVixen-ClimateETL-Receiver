"""Download and load NOAA Storm Events (1996-2026) into prancer.storm_events,
enriching forecast-zone events with county_fips via the Census Geocoder.
"""

import csv
from datetime import datetime, timezone
import gzip
from pathlib import Path
import re

import requests

from course_db import connect

TEAM = "prancer"
BASE_URL = "https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/"
HEADERS = {"User-Agent": "36-614 project (ahou@andrew.cmu.edu)"}
RAW_DIR = Path("data/raw/storm_events")
YEARS = range(1996, 2027)       # 1996+ covers all 48 standardized NOAA storm event types
MAX_GEOCODE_LOOKUPS = 25        # caches unique rounded (lat, lon) lookups per run

# for state identification
STATE_ABBR = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO", "09": "CT",
    "10": "DE", "11": "DC", "12": "FL", "13": "GA", "15": "HI", "16": "ID", "17": "IL",
    "18": "IN", "19": "IA", "20": "KS", "21": "KY", "22": "LA", "23": "ME", "24": "MD",
    "25": "MA", "26": "MI", "27": "MN", "28": "MS", "29": "MO", "30": "MT", "31": "NE",
    "32": "NV", "33": "NH", "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND",
    "39": "OH", "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC", "46": "SD",
    "47": "TN", "48": "TX", "49": "UT", "50": "VT", "51": "VA", "53": "WA", "54": "WV",
    "55": "WI", "56": "WY",
}
# for monetary values
MULTIPLIERS = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}


def parse_damage(val: str | None) -> float | None:
    """Convert NOAA damage strings like '25K' or '1.5M' into USD."""
    if not val or not val.strip():
        return None
    s = val.strip().upper()
    if s[-1] in MULTIPLIERS:
        num = s[:-1].strip()
        return float(num) * MULTIPLIERS[s[-1]] if num else 0.0
    try:
        return float(s)
    except ValueError:
        return None


def parse_noaa_ts(val: str | None) -> datetime | None:
    """Parse NOAA timestamp '15-MAY-21 14:30:00' into UTC TIMESTAMPTZ."""
    if not val or not val.strip():
        return None
    return datetime.strptime(val.strip(), "%d-%b-%y %H:%M:%S").replace(tzinfo=timezone.utc)


def geocode_point(lat: float, lon: float) -> str | None:
    """Resolve (lat, lon) to a 5-digit county FIPS via the Census Geocoder API."""
    url = "https://census.gov"
    params = {
        "x": lon,
        "y": lat,
        "benchmark": "Public_AR_Current",
        "vintage": "Current_Current",
        "format": "json",
    }
    try:
        r = requests.get(url, params=params, timeout=3)
        r.raise_for_status()
        counties = r.json().get("result", {}).get("geographies", {}).get("Counties", [])
        if counties:
            return counties[0].get("GEOID")
    except Exception:
        return None
    return None


# 1. Fetch NCEI Storm Events directory listing
RAW_DIR.mkdir(parents=True, exist_ok=True)
idx_resp = requests.get(BASE_URL, headers=HEADERS, timeout=30)
idx_resp.raise_for_status()
index_html = idx_resp.text

with connect(team=TEAM) as conn:
    valid_fips = {
        fips.strip()
        for (fips,) in conn.execute("SELECT county_fips FROM course.counties").fetchall()
    }
    geocode_cache: dict[tuple[float, float], str | None] = {}

    for yr in YEARS:
        matches = re.findall(
            rf'href="(StormEvents_details-ftp_v1\.0_d{yr}_c\d+\.csv\.gz)"',
            index_html,
        )
        if matches:
            fname = sorted(matches)[-1]
            fpath = RAW_DIR / fname
            if not fpath.exists():
                print(f"Downloading {fname}...")
                resp = requests.get(BASE_URL + fname, headers=HEADERS, timeout=120)
                resp.raise_for_status()
                fpath.write_bytes(resp.content)
        else:
            cached = sorted(RAW_DIR.glob(f"StormEvents_details-ftp_v1.0_d{yr}_c*.csv.gz"))
            if not cached:
                continue
            fpath = cached[-1]

        # 2. Parse rows, scrub corrupt coordinates, and resolve county_fips
        rows = []
        with gzip.open(fpath, "rt", encoding="utf-8", errors="replace", newline="") as f:
            for r in csv.DictReader(f):
                st_fp = (r.get("STATE_FIPS") or "").strip().zfill(2)
                if st_fp not in STATE_ABBR:
                    continue
                cz_type = (r.get("CZ_TYPE") or "").strip()
                if cz_type not in ("C", "Z", "M"):
                    continue
                cz_fp = (r.get("CZ_FIPS") or "").strip().zfill(3)

                lat = float(r["BEGIN_LAT"]) if (r.get("BEGIN_LAT") or "").strip() else None
                lon = float(r["BEGIN_LON"]) if (r.get("BEGIN_LON") or "").strip() else None
                end_lat = float(r["END_LAT"]) if (r.get("END_LAT") or "").strip() else None
                end_lon = float(r["END_LON"]) if (r.get("END_LON") or "").strip() else None

                # Null out corrupt historical coordinates outside valid Earth bounds (e.g., 1997 KS lat=97.1)
                if lat is not None and not (-90 <= lat <= 90):
                    lat = None
                if lon is not None and not (-180 <= lon <= 180):
                    lon = None
                if end_lat is not None and not (-90 <= end_lat <= 90):
                    end_lat = None
                if end_lon is not None and not (-180 <= end_lon <= 180):
                    end_lon = None

                county_fips = None
                fips_src = "unmatched"
                if cz_type == "C" and f"{st_fp}{cz_fp}" in valid_fips:
                    county_fips = f"{st_fp}{cz_fp}"
                    fips_src = "direct"
                elif lat is not None and lon is not None:
                    key = (round(lat, 2), round(lon, 2))
                    if key not in geocode_cache and len(geocode_cache) < MAX_GEOCODE_LOOKUPS:
                        geocode_cache[key] = geocode_point(key[0], key[1])
                    if geocode_cache.get(key) in valid_fips:
                        county_fips = geocode_cache[key]
                        fips_src = "geocoder"

                begin_ts = parse_noaa_ts(r.get("BEGIN_DATE_TIME"))
                if begin_ts is None:
                    continue

                rows.append((
                    int(r["EVENT_ID"]),
                    int(r["EPISODE_ID"]) if (r.get("EPISODE_ID") or "").strip() else None,
                    st_fp,
                    STATE_ABBR[st_fp],
                    (r.get("STATE") or "").strip(),
                    cz_type,
                    cz_fp,
                    county_fips,
                    (r.get("EVENT_TYPE") or "").strip(),
                    begin_ts,
                    parse_noaa_ts(r.get("END_DATE_TIME")),
                    max(0, int(r.get("INJURIES_DIRECT") or 0)),
                    max(0, int(r.get("INJURIES_INDIRECT") or 0)),
                    max(0, int(r.get("DEATHS_DIRECT") or 0)),
                    max(0, int(r.get("DEATHS_INDIRECT") or 0)),
                    parse_damage(r.get("DAMAGE_PROPERTY")),
                    parse_damage(r.get("DAMAGE_CROPS")),
                    float(r["MAGNITUDE"]) if (r.get("MAGNITUDE") or "").strip() else None,
                    (r.get("MAGNITUDE_TYPE") or "").strip() or None,
                    lat,
                    lon,
                    end_lat,
                    end_lon,
                    fips_src,
                ))

        # 3. Stage via COPY and upsert into storm_events, committing each year
        conn.execute("DROP TABLE IF EXISTS pg_temp.stage_storms")
        conn.execute(
            """
            CREATE TEMP TABLE stage_storms (
              LIKE storm_events INCLUDING DEFAULTS
            ) ON COMMIT DROP
            """
        )
        with conn.cursor() as cur:
            with cur.copy(
                """
                COPY stage_storms (
                  event_id, episode_id, state_fips, state_abbr, state_name,
                  cz_type, cz_fips, county_fips, event_type, begin_ts, end_ts,
                  injuries_direct, injuries_indirect, deaths_direct, deaths_indirect,
                  damage_property_usd, damage_crops_usd, magnitude, magnitude_type,
                  begin_lat, begin_lon, end_lat, end_lon, fips_source
                ) FROM STDIN
                """
            ) as copy:
                for row in rows:
                    copy.write_row(row)

            cur.execute(
                """
                INSERT INTO storm_events
                SELECT * FROM stage_storms
                ON CONFLICT (event_id) DO UPDATE SET
                  damage_property_usd = EXCLUDED.damage_property_usd,
                  damage_crops_usd = EXCLUDED.damage_crops_usd,
                  deaths_direct = EXCLUDED.deaths_direct,
                  deaths_indirect = EXCLUDED.deaths_indirect,
                  county_fips = COALESCE(EXCLUDED.county_fips, storm_events.county_fips),
                  fips_source = EXCLUDED.fips_source
                """
            )
        conn.commit()
        print(f"Year {yr}: staged and merged {len(rows)} storm events.")

    (total,) = conn.execute("SELECT count(*) FROM storm_events").fetchone()
    print(f"Done! storm_events now has {total} total rows.")
