# Technical specification: [system name]

> **What goes here:** the design of your system, in the format professional data teams
> use for a technical specification. Fill in every section. Repeat the table, program, and
> query sections once for each table, program, and client query. The examples come from
> the shared course weather data; replace them, and delete these notes before you tag
> `handoff`. Keep this document in step with `sql/schema.sql` and `src/`.

## Document header

| | |
|---|---|
| **Document name** | `TS_prancer_climate-risk-underwriting` |
| **Authors** | Team Prancer |
| **Created on** | 2026-11-10 |
| **Repository** | `<https://github.com/mrmellors/climate-etl-prancer>` |
| **Knowledge transfer log** | [`docs/kt-log.md`](kt-log.md) |

## Sign-offs

| Role | Name | Date |
|---|---|---|
| Builders (development) | Team Prancer | November 20, 2026 |
| Receivers (taking ownership) | Team Vixen | November 23, 2026 |

## Revision history

| Author | Reason for revision | Version | Date | Git tag or commit |
|---|---|---|---|---|
| | Initial authoring | 1.0 | | `handoff` |
| | | | | |

## Objects list

> Every file a receiver needs to run or change the system.

| Object | Type | Description |
|---|---|---|
| `sql/schema.sql` | SQL script | Creates every table, key, and constraint |
| `src/refresh.py` | Program | Inbound interface: pulls new data and appends it safely |
| `src/report.py` | Program | Client report that takes parameters |
| `sql/queries/` | Queries | Client query library |
| `sql/tests/` | Tests | Checks that return zero rows when the data and queries are right |
| `reports/report.qmd` | Report | Part II report and visualizations |

## High-level technical overview

> One paragraph: what the system does for the client, and how. Then your **scope**, one
> of your most important design decisions: which sources, which region, how many years,
> what's out of scope, and why.

This system provides a property and casualty (P&C) insurer's underwriting and exposure team with an integrated PostgreSQL risk database combining historical storm losses, hurricane tracks, daily station weather, live NWS conditions, and county-level socioeconomic exposure. It supports state-level flood frequency versus severity analysis, seasonal hail exposure pricing, multi-decade billion-dollar storm episode tracking, and hazard under-counting audits comparing property damage against human fatalities.

## Process flow diagram

> How data move from the sources to the client. Replace the example with your own; Mermaid
> diagrams like this one display on GitHub.

```mermaid
flowchart LR
    CLI["src/refresh.py<br/>(--team, --source,<br/>--start, --end, --dry-run)"] --> TX

    subgraph TX["Atomic PostgreSQL Transaction (course_db.connect)"]
        direction LR

        subgraph S1["1. Weather Feeds (ghcn &amp; nws)"]
            direction TB
            W_IN["course.observations &amp;<br/>NWS API (Stations for SE Region)"] -->|Load into| T1[("stations, observations,<br/>nws_observations")]
        end

        subgraph S2["2. Hazard Archives (storms &amp; hurdat)"]
            direction TB
            H_IN["NOAA NCEI Bulk CSVs &amp;<br/>NHC HURDAT2 (1980+)"] -->|Load into| T2[("storm_events,<br/>hurdat_storms, hurdat_tracks")]
        end

        subgraph S3["3. Exposure Data (census)"]
            direction TB
            C_IN["2024 U.S. Census ACS 5-Yr API<br/>(CENSUS_API_KEY)"] -->|Load into| T3[("county_demographics")]
        end

        subgraph S4["4. Staging &amp; Validation Gate"]
            direction TB
            STG["pg_temp.stage_* (ON COMMIT DROP)<br/>+ run_checks() &amp; FIPS/Coord Bounds"] -->|ON CONFLICT| UPS["Upsert Target Tables"]
        end

        S1 --> S2 --> S3 --> S4

        S1 -.-> LOG[("ingestion_runs<br/>(logs source, staged, inserted, updated)")]
        S2 -.-> LOG
        S3 -.-> LOG
        S4 -.-> LOG
    end

    TX --> DRY{"--dry-run?"}
    DRY -->|Yes| RB["psycopg.Rollback()<br/>(No Changes Saved)"]
    DRY -->|No| CM["Commit &rarr; Schema<br/>(prancer / vixen)"]
    CM --> RPT["src/report.py &amp;<br/>sql/queries/q01–q08 + tests"]
```

## ER diagram

> Every table, its primary and foreign keys, and how the tables relate. Once your tables
> exist, compare it with VS Code's **Visualize Schema** on your team's schema: every line
> here should match a foreign key there.

```mermaid
erDiagram
    COURSE_COUNTIES {
        char_5 county_fips PK "Shared reference table"
        char_2 state
        text name
        numeric land_sq_mi
        double lat
        double lon
    }

    COUNTY_DEMOGRAPHICS {
        char_5 county_fips PK "Matches course.counties"
        text county_name
        int acs_year
        int population
        numeric median_income
        numeric median_home_value
        int housing_units
    }

    STORM_EVENTS {
        bigint event_id PK
        bigint episode_id
        char_2 state_fips
        char_2 state_abbr
        text state_name
        char_1 cz_type
        varchar_3 cz_fips
        char_5 county_fips "Matches course.counties (nullable)"
        text event_type
        timestamptz begin_ts
        timestamptz end_ts
        int injuries_direct
        int injuries_indirect
        int deaths_direct
        int deaths_indirect
        numeric damage_property_usd
        numeric damage_crops_usd
        numeric magnitude
        text magnitude_type
        double begin_lat
        double begin_lon
        double end_lat
        double end_lon
        text fips_source
    }

    HURDAT_STORMS {
        text storm_id PK
        text storm_name
        char_2 basin
        int cyclone_number
        int season_year
        int num_track_points
    }

    HURDAT_TRACKS {
        bigint track_id PK
        text storm_id FK
        timestamptz observed_at
        char_1 record_identifier
        text system_status
        double lat
        double lon
        int max_wind_kt
        int min_pressure_mb
    }

    STATIONS {
        text station_id PK
        text name
        char_2 state
        char_5 county_fips "Nearest course.counties"
        double lat
        double lon
        numeric elevation
    }

    OBSERVATIONS {
        bigint obs_id PK
        text station_id FK
        date date
        numeric tmax
        numeric tmin
        numeric precip
    }

    NWS_OBSERVATIONS {
        text station_id PK
        timestamptz observed_at PK
        double lat
        double lon
        numeric temperature_c
        numeric dewpoint_c
        numeric wind_speed_kmh
        numeric wind_gust_kmh
        numeric barometric_pressure_pa
        numeric relative_humidity_pct
        text text_description
    }

    NWS_ALERTS {
        text alert_id PK
        text event
        text severity
        text certainty
        text urgency
        text area_desc
        char_5_arr county_fips "Array of 5-digit FIPS"
        timestamptz effective_at
        timestamptz expires_at
        text headline
    }

    INGESTION_RUNS {
        bigint run_id PK
        timestamptz started_at
        text source
        int rows_staged
        int rows_inserted
        int rows_updated
    }

    COURSE_COUNTIES ||--o| COUNTY_DEMOGRAPHICS : "enriches (1:1)"
    COURSE_COUNTIES ||--o{ STORM_EVENTS : "locates event (1:N)"
    COURSE_COUNTIES ||--o{ STATIONS : "locates station (1:N)"
    COURSE_COUNTIES }o..o{ NWS_ALERTS : "targets via county_fips[] (M:N)"
    HURDAT_STORMS ||--|{ HURDAT_TRACKS : "contains fixes (1:N)"
    STATIONS ||--o{ OBSERVATIONS : "records daily (1:N)"
    HURDAT_TRACKS }o..o{ STATIONS : "spatial proximity (lat/lon)"
```

## Assumptions

- *(example)* The GHCN-Daily yearly files are reachable from the course server.
- *(example)* A station with no observation row on a date is treated as not reporting,
  not as a dry day.

## Dependencies

| Source | Where it comes from | Access and terms | Updates | Tables it feeds |
|---|---|---|---|---|
| NOAA Storm Events | NOAA NCEI, <https://noaa.gov> | Public bulk `.csv.gz` files; no key needed | Monthly (with ~60–90 day reporting lag) | `storm_events` |
| NHC HURDAT2 | National Hurricane Center, <https://noaa.gov> | Public text file; requires `User-Agent` header | Seasonal (post-storm reanalysis) | `hurdat_storms`, `hurdat_tracks` |
| GHCN-Daily | Shared server tables `course.stations` & `course.observations` (from NOAA NCEI) | Course server access via `course_db` | Daily (archive finalized 45–60 days after month-end) | `stations`, `observations` |
| NWS Web API | National Weather Service, <https://weather.gov> | Public GeoJSON API; requires `User-Agent` and `Accept: application/geo+json`; max 500 rows/request; 7-day rolling retention | Hourly / Live | `nws_observations`, `nws_alerts` |
| Census ACS 5-Year & Geocoder | U.S. Census Bureau, <https://census.gov> & <https://census.gov> | Free `CENSUS_API_KEY` in local environment (`os.environ["CENSUS_API_KEY"]`); geocoder requires no key | Annual (ACS 5-year) | `county_demographics`, `storm_events.county_fips` |
| Shared Course Reference | `course.counties` on `mads_f26` | Read-only (`SELECT`) on course server | Static | Spatial lookup for `county_fips` |

- **Runtime environment:** Python 3.13 with packages listed in `requirements.txt` (`psycopg`, `requests`, etc.) and PostgreSQL on `mads_f26`.

## Roles and authorizations

| Role | Who holds it | Can do |
|---|---|---|
| `prancer_write` | Team Prancer until Nov 23, then Team Vixen | Create, alter, insert, update, and drop objects in `prancer` |
| `prancer_read` | Team Prancer after Nov 23, plus instructional staff | `SELECT` from all tables in `prancer` |

## Design decisions

> Three to five of your main choices, a short paragraph each: the choice, the
> alternative you rejected, and why.

*(example)* **Observations get their own table**, one row per station per date, rather
than one column per measurement type in a "long" table. Most client queries compare
temperature and precipitation on the same day, which a long table would turn into a
self-join. Enforced by `UNIQUE (station_id, date)`.

## Known issues and limitations

> Everything a receiver should know before trusting a result: proxy measures (named as
> proxies), limitations, and unfinished work. Be specific.

- *(example)* The current year is partial; compare it with earlier years only by month,
  and only for complete months.

---

## Database table: `stations` (example)

> One section per table.

| | |
|---|---|
| **Description** | U.S. weather stations from the GHCN-Daily station list |
| **Row unit** | One weather station |
| **Primary key** | `station_id` |
| **Referenced by** | `observations.station_id` |

| Field | Description | Data source | Data type | Key | Units |
|---|---|---|---|---|---|
| `station_id` | GHCN station ID, e.g. `USW00094823` | GHCN station list | TEXT | X | |
| `name` | Station name | GHCN station list | TEXT | | |
| `state` | Two-letter state code; can be missing | GHCN station list | CHAR(2) | | |
| `lat` | Latitude | GHCN station list | DOUBLE PRECISION | | degrees |
| `lon` | Longitude; negative in the U.S. | GHCN station list | DOUBLE PRECISION | | degrees |
| `elevation` | Elevation; missing for some stations | GHCN station list | NUMERIC | | meters |

## Program: `src/refresh.py` (example)

> One section per program.

| | |
|---|---|
| **Description** | Pulls new observations and appends them safely |
| **Type** | Python command (extract, transform, load) |
| **Status** | In production |
| **Parameters** | `--team`, `--start`, `--end` (exclusive), `--dry-run` |
| **Output** | Prints rows staged, inserted, and updated; adds a row to `ingestion_runs` |

**Pseudocode**

1. **Fetch:** read the source rows for the date range.
2. **Stage:** copy them into a temporary staging table.
3. **Validate:** count duplicate station-dates, negative precipitation, `tmax` below
   `tmin`, and unknown stations. If any check fails, stop; the transaction rolls back and
   nothing changes.
4. **Merge:** insert new rows and update changed ones, matched on `(station_id, date)`. An
   identical rerun changes nothing.
5. **Log:** record the counts in `ingestion_runs`.

## Query: `q01-rainy-days-by-station` (example)

> One section per client query.

| | |
|---|---|
| **Client question** | Which Pennsylvania stations reported rain on the most days in September 2025? |
| **Row unit** | One station |
| **Test** | `sql/tests/t01-rainy-days-match.sql` |

| Field | Description | Source |
|---|---|---|
| `station_id` | Station ID | `stations` |
| `name` | Station name | `stations` |
| `rainy_days` | Days with precipitation above 0 | `observations` |
