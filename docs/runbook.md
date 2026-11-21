# Runbook

## Connect

Team Prancer's PostgreSQL database is hosted on the CMU course server (`mads_f26`) under the `prancer` schema. The system uses CMU Microsoft Entra authentication through the course-provided `course_db.py` module.

### 1. Set up the Python environment

From the repository root, run:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

In VS Code, select the `.venv` Python interpreter.

### 2. Connect to PostgreSQL

If necessary, configure your CMU username:

```bash
export PGUSER="YOUR_ANDREW_ID@andrew.cmu.edu"
```

Test the connection:

```bash
python course_db.py
```

A successful connection should identify the `mads_f26` database.

From Python:

```python
from course_db import connect

conn = connect(team="prancer")

print(conn.execute(
    "SELECT current_database(), current_schema()"
).fetchone())
```

The expected database and schema are `mads_f26` and `prancer`.

For direct SQL connections:

```sql
SET ROLE prancer_write;
SET search_path = prancer, course, public;
```

Do not rerun the entire `sql/schema.sql` against an already populated database without checking its effects.

## Refresh the data

The refresh pipeline is controlled by `src/refresh.py`. Each source can be refreshed independently because the datasets have different update schedules.

Run all commands from the repository root with `.venv` activated.

The primary analytical scope is Texas, Louisiana, Florida, Georgia, South Carolina, and North Carolina. Some loaders may ingest records outside these states; the client SQL queries apply geographic filters.

### 1. GHCN-Daily — Daily

GHCN weather observations are retrieved from the shared course database and merged into `prancer.observations`.

```bash
python src/refresh.py --team prancer --source ghcn --start 2025-09-01 --end 2025-10-01
```

Recorded output from a successful initial load:

```text
[ghcn (2025-09-01 to 2025-10-01)] 15070 rows staged, 15070 inserted, 0 updated.
```

When the same records have already been loaded and remain unchanged, subsequent runs should report zero inserts and updates.

The current loader reads the requested date range from `course.observations` without restricting the source records to the six target states.

### 2. National Weather Service — Hourly

The NWS loader retrieves recent observations from five configured stations: KPIT, KMIA, KHOU, KDFW, and KORD.

```bash
python src/refresh.py --team prancer --source nws
```

Recorded output:

```text
[nws (live observations)] 2500 rows staged, 4 inserted, 0 updated.
```

Counts may change as the API updates.

The current `refresh_nws()` function refreshes `nws_observations`. Refreshing `nws_alerts` requires a separate verified workflow.

### 3. NOAA Storm Events — Monthly

The NOAA Storm Events loader downloads NOAA NCEI bulk CSV files, validates records, and merges them into `prancer.storm_events`.

```bash
python src/refresh.py --team prancer --source storms --start 2026-01-01 --end 2026-12-31
```

Recorded output:

```text
[noaa_storms (2026-01-01 to 2026-12-31)] 48150 rows staged, 0 inserted, 0 updated.
```

The loader stores downloaded files in `data/raw/storm_events/`.

The `--end` argument is exclusive. The current loader is not consistently restricted to the six-state analytical region.

### 4. HURDAT2 — Seasonal

HURDAT2 provides Atlantic hurricane best-track observations, including storm identifiers, timestamps, geographic coordinates, and wind speeds.

```bash
python src/refresh.py --team prancer --source hurdat
```

Recorded output:

```text
[hurdat2 (atlantic best tracks)] 21335 rows staged, 0 inserted, 0 updated.
```

The loader refreshes `hurdat_storms` and `hurdat_tracks`.

Client queries focus on Atlantic storms and track points within the Southeast coastal region.

### 5. Census ACS — Annual

The Census loader retrieves county demographic information from the 2024 ACS 5-year estimates, including population, median income, median home value, and housing units.

The current loader requires a Census API key supplied through an environment variable.

```bash
export CENSUS_API_KEY="YOUR_CENSUS_API_KEY"
python src/refresh.py --team prancer --source census --dry-run
```

Recorded output:

```text
[census_acs5 (county demographics)] 3222 rows staged, 0 inserted, 0 updated.
Dry run: undoing all changes.
```

Remove `--dry-run` when a permanent refresh is required and authorized.

### 6. Test a refresh without saving changes

Use `--dry-run` with any supported source:

```bash
python src/refresh.py --team prancer --source ghcn --start 2025-09-01 --end 2025-10-01 --dry-run
```

A successful dry run reports the number of rows staged, inserted, and updated, followed by:

```text
Dry run: undoing all changes.
```

The refresh runs inside a PostgreSQL transaction. The dry-run option intentionally rolls back the changes, including the ingestion log entry.

Execution times vary depending on source size, network availability, and database performance. Verified runtime benchmarks are not currently documented.

## Check the output

After each refresh, verify table counts, date coverage, SQL test results, and database storage.

### 1. Confirm that the tables exist

```sql
SELECT tablename
FROM pg_tables
WHERE schemaname = 'prancer'
ORDER BY tablename;
```

The primary tables include:

| Table | Contents |
|---|---|
| `storm_events` | NOAA severe-weather events |
| `hurdat_storms` | Hurricane metadata |
| `hurdat_tracks` | Hurricane track observations |
| `stations` | GHCN station metadata |
| `observations` | Daily station observations |
| `nws_observations` | Recent NWS observations |
| `nws_alerts` | NWS weather alerts |
| `county_demographics` | ACS county demographics |
| `ingestion_runs` | Refresh execution history |

### 2. Check row counts and newest dates

Storm Events:

```sql
SELECT
    COUNT(*) AS total_events,
    MIN(begin_ts) AS earliest_event,
    MAX(begin_ts) AS latest_event
FROM prancer.storm_events;
```

GHCN observations:

```sql
SELECT
    COUNT(*) AS total_observations,
    MIN(date) AS earliest_date,
    MAX(date) AS latest_date
FROM prancer.observations;
```

Hurricane tracks:

```sql
SELECT
    COUNT(*) AS total_tracks,
    MIN(observed_at) AS earliest_track,
    MAX(observed_at) AS latest_track
FROM prancer.hurdat_tracks;
```

NWS observations:

```sql
SELECT
    COUNT(*) AS total_observations,
    MAX(observed_at) AS latest_observation
FROM prancer.nws_observations;
```

Census demographics:

```sql
SELECT
    COUNT(*) AS total_counties,
    MAX(acs_year) AS latest_acs_year
FROM prancer.county_demographics;
```

Compare results with the expected date coverage and source update schedules.

### 3. Verify Southeast geographic coverage

The project's analytical scope includes:

| State | State FIPS |
|---|---|
| Texas | 48 |
| Louisiana | 22 |
| Florida | 12 |
| Georgia | 13 |
| South Carolina | 45 |
| North Carolina | 37 |

Check Storm Events coverage:

```sql
SELECT
    state_fips,
    COUNT(*) AS total_events
FROM prancer.storm_events
WHERE state_fips IN ('48', '22', '12', '13', '45', '37')
GROUP BY state_fips
ORDER BY state_fips;
```

All six states should be represented for the intended historical analysis.

### 4. Check ingestion history

```sql
SELECT *
FROM prancer.ingestion_runs
LIMIT 10;
```

The refresh output reports:

- `rows_staged`: Records prepared for loading.
- `rows_inserted`: New records added.
- `rows_updated`: Existing records changed.

For unchanged source data, rerunning the refresh should normally result in zero inserts and updates.

### 5. Execute the client SQL queries and tests

The eight client queries are located in `sql/queries/`, with corresponding validation tests in `sql/tests/`.

During November 20 validation, all eight client queries executed successfully.

| Query | Rows returned |
|---|---:|
| Q01 — Flood damage by year | 66 |
| Q02 — Flood frequency versus severity | 6 |
| Q03 — Hail seasonality | 70 |
| Q04 — Billion-dollar episodes | 4 |
| Q05 — Fatalities versus damage | 29 |
| Q06 — County damage per capita | 25 |
| Q07 — Hurricane peak winds | 25 |
| Q08 — Hurricane station proximity | 100 |

All eight corresponding `t01`–`t08` tests returned zero rows.

**A passing test returns zero rows.** Nonempty results indicate conditions requiring investigation.

The current tests primarily assess data consistency and selected calculations, not every aggregate independently.

The additional `t00` database-validation scripts are separate and require further review.

### 6. Check database storage

The course storage limit is **8 GB per team**, including indexes.

```sql
SELECT
    pg_size_pretty(
        SUM(pg_total_relation_size(c.oid))
    ) AS team_size
FROM pg_class AS c
JOIN pg_namespace AS n
    ON n.oid = c.relnamespace
WHERE n.nspname = 'prancer'
  AND c.relkind IN ('r', 'm');
```

Check the storage usage after large source loads.

Avoid unnecessary nationwide data ingestion when only the Southeast region is needed for the client analyses.

## When something fails

| What you see | What it means | What to do |
|---|---|---|
| `ModuleNotFoundError: No module named 'course_db'` | Python cannot locate the course helper | Confirm `src/course_db.py` exists and run from the repository root |
| CMU authentication error | Connection or account authentication failed | Verify `PGUSER`, complete CMU sign-in, and check permissions |
| `Missing CENSUS_API_KEY environment variable` | Census API key is missing | Set the environment variable and rerun |
| HTTP error or timeout | External data source is unavailable | Check network connection and retry |
| Validation failure | Source data failed validation | Inspect records, document the issue, and rerun after resolving it |
| `relation does not exist` | Required table is missing or wrong schema is active | Check `pg_tables`, team role, and schema definition |
| `column does not exist` | Query and table definitions differ | Compare the SQL against the current database columns |
| Duplicate-key violation | A record conflicts with an existing key | Investigate the primary key and merge logic |
| Zero rows inserted | Data may already be current, or the date range contains no new records | Inspect current row counts and source dates |
| Storage approaches 8 GB | Database is nearing the storage limit | Restrict unnecessary source coverage and inspect table sizes |

A failed transaction should roll back changes from that database transaction.

Downloaded raw files may remain on disk because PostgreSQL transactions do not roll back filesystem changes.

## Recover

### 1. Identify the failing source

Read the terminal error and determine whether the failure occurred during download, parsing, staging, validation, or merging.

### 2. Verify the database connection

```bash
python src/course_db.py
```

Check that the database is accessible and that the appropriate Team Prancer tables exist.

### 3. Check for partial changes

The refresh runs inside `conn.transaction()`.

If an error occurs, the active transaction should roll back. Previously committed records should remain unchanged.

Verify using the affected table's row count and `ingestion_runs`.

### 4. Resolve the original problem

For invalid records, inspect the source data and validation rules.

For database errors, compare the actual table structure with `sql/schema.sql`.

For API failures, verify source availability and required configuration.

Document significant issues in `docs/technical-spec.md`.

### 5. Retry with a dry run

For example:

```bash
python src/refresh.py --team prancer --source ghcn --start 2025-09-01 --end 2025-10-01 --dry-run
```

Confirm that the refresh completes and prints:

```text
Dry run: undoing all changes.
```

### 6. Run the actual refresh

Once the dry run succeeds:

```bash
python src/refresh.py --team prancer --source ghcn --start 2025-09-01 --end 2025-10-01
```

### 7. Verify recovery

Check row counts, date coverage, ingestion history, and corresponding SQL tests.

If needed, rerun the refresh to confirm it does not create duplicate records.

Do not drop populated tables or rebuild the database without authorization.

## Who owns what

### Builders — Team Prancer

Team Prancer developed the Climate Risk Analytics system and is responsible for its original database architecture, ingestion pipelines, SQL queries, tests, and documentation.

| Component | Original responsibility |
|---|---|
| Database architecture and core ingestion pipeline | Ainika Hou |
| NOAA Storm Events and hurricane ingestion | Matt Mellors |
| Client SQL queries and corresponding tests | Bruck Setu |
| Integration, testing, and documentation | Team Prancer collectively |

Responsibilities may overlap across team members.

### Receivers

Team Vixen takes over the Climate Risk Analytics system during the November 23 knowledge-transfer session.

The receiving team will be responsible for running refreshes, checking data quality, maintaining the system, and investigating failures.

Team Prancer will explain its original design choices and known limitations during the handoff.

Team Vixen should use `README.md`, `docs/technical-spec.md`, and this runbook as the primary operating documentation.
