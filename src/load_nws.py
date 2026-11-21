"""Load NWS station observations (limit=500) and active alerts into prancer."""

import requests

from course_db import connect

TEAM = "prancer"
# Internet responses of airport stations in southern states
STATIONS = [
    # Texas (TX)
    "KDFW",  # Dallas Fort Worth International Airport (Dallas/Fort Worth, TX)
    "KIAH",  # George Bush Intercontinental Airport (Houston, TX)
    "KAUS",  # Austin-Bergstrom International Airport (Austin, TX)
    "KSAT",  # San Antonio International Airport (San Antonio, TX)

    # Louisiana (LA)
    "KMSY",  # Louis Armstrong New Orleans International Airport (New Orleans, LA)
    "KBTR",  # Baton Rouge Metropolitan Airport (Baton Rouge, LA)
    "KSHV",  # Shreveport Regional Airport (Shreveport, LA)

    # Florida (FL)
    "KMIA",  # Miami International Airport (Miami, FL)
    "KMCO",  # Orlando International Airport (Orlando, FL)
    "KTPA",  # Tampa International Airport (Tampa, FL)
    "KJAX",  # Jacksonville International Airport (Jacksonville, FL)

    # Georgia (GA)
    "KATL",  # Hartsfield-Jackson Atlanta International Airport (Atlanta, GA)
    "KSAV",  # Savannah/Hilton Head International Airport (Savannah, GA)

    # North Carolina (NC)
    "KCLT",  # Charlotte Douglas International Airport (Charlotte, NC)
    "KRDU",  # Raleigh-Durham International Airport (Raleigh/Durham, NC)

    # South Carolina (SC)
    "KCHS",  # Charleston International Airport (Charleston, SC)
    "KCAE",  # Columbia Metropolitan Airport (Columbia, SC)
    "KGSP",  # Greenville-Spartanburg International Airport (Greer, SC)
]
HEADERS = {
    "User-Agent": "36-614 project (ahou@andrew.cmu.edu)",              
    "Accept": "application/geo+json",
}

obs_rows = []
for stn in STATIONS:
    url = f"https://api.weather.gov/stations/{stn}/observations"
    # 1. Ask the NWS API for up to 500 observations per station and active alerts.
#    raise_for_status() stops the script here if the API answered with an error
#    instead of loading nothing.
    response = requests.get(url, params={"limit": 500}, headers=HEADERS, timeout=30)
    response.raise_for_status()
    data = response.json()
    print(f"Station {stn}: API sent {len(data['features'])} observations.")

    # 2. Turn the response into rows: one tuple per observation, in the order of
    #    the table's columns. Missing values come back as None -> SQL NULL.
    for feature in data["features"]:
        obs = feature["properties"]
        lon, lat = feature["geometry"]["coordinates"]
        obs_rows.append((
            obs["stationId"],
            obs["timestamp"],
            lat,                                           # decimal degrees
            lon,                                           # decimal degrees
            obs["temperature"]["value"],                   # degrees Celsius (wmoUnit:degC)
            obs["dewpoint"]["value"],                      # degrees Celsius (wmoUnit:degC)
            obs["windSpeed"]["value"],                     # kilometers per hour (wmoUnit:km_h-1)
            obs["windGust"]["value"],                      # kilometers per hour (wmoUnit:km_h-1)
            obs["barometricPressure"]["value"],            # Pascals (wmoUnit:Pa)
            obs["relativeHumidity"]["value"],              # percent (wmoUnit:percent)
            obs["textDescription"],
        ))
print(f"Read {len(obs_rows)} total observations from the API.")

alert_response = requests.get(
    "https://api.weather.gov/alerts",
    params={"status": "actual"},
    headers=HEADERS,
    timeout=30,
)
alert_response.raise_for_status()
alert_features = alert_response.json().get("features", []) if alert_response.text.strip() else []

alert_rows = []
for feature in alert_features:
    props = feature["properties"]
    same_codes = props.get("geocode", {}).get("SAME", [])
    fips_list = [c[1:] for c in same_codes if len(c) == 6 and c.startswith("0")]
    alert_rows.append((
        props["id"],
        props["event"],
        props.get("severity"),
        props.get("certainty"),
        props.get("urgency"),
        props.get("areaDesc"),
        fips_list or None,
        props.get("effective"),
        props.get("expires"),
        props.get("headline"),
    ))
print(f"Read {len(alert_rows)} active alerts from the API.")

# 3. Merge the rows, sending every value as a parameter. Nothing is saved until
#    this block ends without an error.
with connect(team=TEAM) as conn:
    (before_obs,) = conn.execute("SELECT count(*) FROM nws_observations").fetchone()
    (before_al,) = conn.execute("SELECT count(*) FROM nws_alerts").fetchone()
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO nws_observations (
              station_id, observed_at, lat, lon, temperature_c, dewpoint_c,
              wind_speed_kmh, wind_gust_kmh, barometric_pressure_pa,
              relative_humidity_pct, text_description
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (station_id, observed_at)
            DO UPDATE SET temperature_c = EXCLUDED.temperature_c,
                          dewpoint_c = EXCLUDED.dewpoint_c,
                          wind_speed_kmh = EXCLUDED.wind_speed_kmh,
                          wind_gust_kmh = EXCLUDED.wind_gust_kmh,
                          barometric_pressure_pa = EXCLUDED.barometric_pressure_pa,
                          relative_humidity_pct = EXCLUDED.relative_humidity_pct,
                          text_description = EXCLUDED.text_description
            """,
            obs_rows,
        )
        cur.executemany(
            """
            INSERT INTO nws_alerts (
              alert_id, event, severity, certainty, urgency, area_desc,
              county_fips, effective_at, expires_at, headline
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (alert_id)
            DO UPDATE SET expires_at = EXCLUDED.expires_at,
                          severity = EXCLUDED.severity
            """,
            alert_rows,
        )
    (after_obs,) = conn.execute("SELECT count(*) FROM nws_observations").fetchone()
    (after_al,) = conn.execute("SELECT count(*) FROM nws_alerts").fetchone()
    print(f"nws_observations had {before_obs} rows and now has {after_obs}.")
    print(f"nws_alerts had {before_al} rows and now has {after_al}.")
