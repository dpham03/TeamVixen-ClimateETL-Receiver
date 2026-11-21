# Runbook

Step-by-step guide for **Team Prancer's** Climate Risk Analytics and P&C Insurance Underwriting database pipeline. 

Team Prancer's PostgreSQL database is hosted on the Carnegie Mellon University course server (`mads_f26`) under the `prancer` schema. The system uses CMU Microsoft Entra authentication through the course-provided `course_db.py` module.

Post-handoff commands below should update to `--team vixen` (`vixen` schema); use `prancer` when inspecting Team Prancer's original build.

---

## Connect

### 1. Set up Python environment

From the repository root, create and activate the virtual environment and install dependencies:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

In VS Code, open the Command Palette (`Cmd+Shift+P` / `Ctrl+Shift+P`), run **Python: Select Interpreter**, and choose `.venv/bin/python`.

### 2. Configure credentials and test `course_db.py`

Export your CMU Andrew email (and `CENSUS_API_KEY` if running `--source census`):

```bash
export PGUSER="YOUR_ANDREW_ID@andrew.cmu.edu"
export CENSUS_API_KEY="YOUR_CENSUS_API_KEY"
```

Verify database connectivity from the repository root:

```bash
python src/course_db.py
```

**Expected output:** Confirms an active Entra-authenticated connection to `mads_f26`.

### 3. Connect from Python

Verify that `course_db.connect()` resolves to your target database and schema:

```bash
python -c "from course_db import connect; conn = connect(team='prancer'); print(conn.execute('SELECT current_database(), current_schema()').fetchone()); conn.close()"
```

**Expected output:**
```text
('mads_f26', 'prancer')
```

### 4. Connect from SQL (`psql` or VS Code PostgreSQL Extension)

Set your team write role and search path at the start of any direct SQL session:

```sql
SET ROLE prancer_write;
SET search_path = prancer, course, public;
SELECT current_user, current_role, current_schema();
```

> **Caution:** Do not re-run `sql/schema.sql` against an already populated schema unless performing an authorized full rebuild.

---

## Refresh the data

All ingestion pipelines are orchestrated by `src/refresh.py` from the repository root with `.venv` activated. Each `--source` runs inside an atomic `conn.transaction()` block with `ON COMMIT DROP` staging tables (`stage_observations`, `stage_nws`, `stage_storms`, `stage_hurdat_tracks`, `stage_census`), so any validation failure rolls back cleanly without partial writes.

The primary analytical scope covers **six Gulf and Southeast states**: Texas (`48`), Louisiana (`22`), Florida (`12`), Georgia (`13`), South Carolina (`45`), and North Carolina (`37`). Some upstream loaders ingest broader national coverage; downstream client queries apply state filters.

### 1. GHCN-Daily Weather Observations — Daily

Pulls daily station temperature (`tmax`, `tmin`) and precipitation (`precip`) from `course.observations`, resolves missing station metadata and nearest `county_fips`, and merges into `observations`.

```bash
python src/refresh.py --team prancer --source ghcn --start 2025-09-01 --end 2025-10-01
```

**Recorded output from initial load:**
```text
[ghcn (2025-09-01 to 2025-10-01)] 15070 rows staged, 15070 inserted, 0 updated.
```
*Note: Re-running an unchanged window reports `0 inserted, 0 updated`.*

### 2. National Weather Service (NWS) Surface Observations — Hourly

Fetches the latest ~500 automated surface observations per station across benchmark airport stations in the Southeast region across states Texas, Louisiana, Florida, Georgia, North Carolina, and South Carolina from `api.weather.gov` into `nws_observations`.

```bash
python src/refresh.py --team prancer --source nws
```

**Recorded output:**
```text
[nws (live observations)] 2500 rows staged, 4 inserted, 0 updated.
```
*Note: Counts vary as live hourly observations arrive. Refreshing `nws_alerts` requires a separate workflow outside `refresh_nws()`.*

### 3. NOAA Storm Events — Monthly

Scrapes the NOAA NCEI Storm Events directory, caches annual `.csv.gz` archives locally in `data/raw/storm_events/`, parses `K/M/B/T` damage multipliers, validates county FIPS codes, and upserts into `storm_events`. (`--end` is exclusive.)

```bash
python src/refresh.py --team prancer --source storms --start 2026-01-01 --end 2026-12-31
```

**Recorded output:**
```text
[noaa_storms (2026-01-01 to 2026-12-31)] 48150 rows staged, 0 inserted, 0 updated.
```

### 4. NHC HURDAT2 Atlantic Best Tracks — Seasonal

Downloads the latest NHC `hurdat2-1851-*.txt` archive, validates track point counts per cyclone (`1980`–present), and merges storm headers into `hurdat_storms` and 6-hourly/landfall fixes into `hurdat_tracks`.

```bash
python src/refresh.py --team prancer --source hurdat
```

**Recorded output:**
```text
[hurdat2 (atlantic best tracks)] 21335 rows staged, 0 inserted, 0 updated.
```

### 5. U.S. Census ACS 5-Year County Demographics — Annual

Fetches 2024 ACS 5-year county estimates (population, median household income, median home value, and housing units) via the Census Data API into `county_demographics`. Requires `CENSUS_API_KEY`.

```bash
export CENSUS_API_KEY="YOUR_CENSUS_API_KEY"
python src/refresh.py --team prancer --source census
```

**Recorded output (with `--dry-run`):**
```text
[census_acs5 (county demographics)] 3222 rows staged, 0 inserted, 0 updated.
Dry run: undoing all changes.
```

### 6. Test any refresh without committing (`--dry-run`)

Append `--dry-run` to execute live downloads, staging checks, and `ON CONFLICT` merges before rolling back the transaction (including the `ingestion_runs` log row):

```bash
python src/refresh.py --team prancer --source ghcn --start 2025-09-01 --end 2025-10-01 --dry-run
```

**Expected output:**
```text
[ghcn (2025-09-01 to 2025-10-01)] 15070 rows staged, 0 inserted, 0 updated.
Dry run: undoing all changes.
```

---

## Check the output

After each refresh, confirm schema tables, row counts, date coverage, SQL test assertions, and storage consumption.

### 1. Confirm all core tables exist

```sql
SELECT tablename
FROM pg_tables
WHERE schemaname = 'prancer'
ORDER BY tablename;
```

| Table | Contents |
|---|---|
| `states` | U.S. state, district, and territory FIPS lookup (`56` rows) |
| `counties` | U.S. county boundaries, land area, and centroids |
| `county_demographics` | 2024 Census ACS 5-year county socioeconomic & housing exposure |
| `storm_events` | NOAA severe-weather events, casualties, and property/crop damage |
| `hurdat_storms` | NHC HURDAT2 tropical cyclone metadata (`1980`–present) |
| `hurdat_tracks` | 6-hourly synoptic, peak intensity, and landfall track fixes |
| `stations` | GHCN-Daily station metadata mapped to `state_fips` and `county_fips` |
| `observations` | Daily GHCN temperature and precipitation observations |
| `nws_observations` | Automated hourly NWS surface observations (`KPIT`, `KMIA`, `KHOU`, `KDFW`, `KORD`) |
| `nws_alerts` | Active NWS weather warnings and watches |
| `ingestion_runs` | Audit log of every `src/refresh.py` execution |

### 2. Check row counts and newest dates loaded

```sql
SELECT 'storm_events' AS table_name, COUNT(*) AS row_count, MIN(begin_ts)::text AS earliest, MAX(begin_ts)::text AS latest FROM prancer.storm_events
UNION ALL
SELECT 'observations', COUNT(*), MIN(date)::text, MAX(date)::text FROM prancer.observations
UNION ALL
SELECT 'hurdat_tracks', COUNT(*), MIN(observed_at)::text, MAX(observed_at)::text FROM prancer.hurdat_tracks
UNION ALL
SELECT 'nws_observations', COUNT(*), MIN(observed_at)::text, MAX(observed_at)::text FROM prancer.nws_observations
UNION ALL
SELECT 'county_demographics', COUNT(*), MIN(acs_year)::text, MAX(acs_year)::text FROM prancer.county_demographics;
```

**Normal baseline expectations (as of November 20 validation):**
* `storm_events`: `~421,037` rows (`1996-01-01` through `2026-08-31`)
* `hurdat_tracks`: `~21,335` track fixes (`1980`–present)
* `county_demographics`: `3,222` U.S. counties (`acs_year = 2024`)

### 3. Verify six-state Gulf & Southeast coverage

Confirm all six target states are populated in `storm_events`:

```sql
SELECT
    s.state_abbr,
    e.state_fips,
    COUNT(*) AS total_events,
    MAX(e.begin_ts)::date AS latest_event
FROM prancer.storm_events AS e
JOIN prancer.states AS s USING (state_fips)
WHERE e.state_fips IN ('48', '22', '12', '13', '45', '37')
GROUP BY s.state_abbr, e.state_fips
ORDER BY e.state_fips;
```

### 4. Audit `ingestion_runs`

```sql
SELECT run_id, started_at, source, rows_staged, rows_inserted, rows_updated
FROM prancer.ingestion_runs
ORDER BY run_id DESC
LIMIT 10;
```

*Normal behavior:* Each non-dry-run refresh appends one row (`rows_staged`, `rows_inserted`, `rows_updated`). Rerunning an unchanged date window yields `rows_inserted = 0` and `rows_updated = 0`.

### 5. Execute client SQL queries (`sql/queries/`) and validation tests (`sql/tests/`)

Run the eight validation test scripts (`t01`–`t08`) against your schema:

```bash
for t in sql/tests/t0[1-8]*.sql; do
    echo "=== Running \$t ==="
    psql -d mads_f26 -v ON_ERROR_STOP=1 -c "SET search_path = prancer, course, public;" -f "\$t"
done
```

**What normal looks like:** **Every passing test returns `0` rows.** Any returned rows indicate data anomalies or broken invariants requiring investigation. (Note: `t00` database-level validation scripts are separate and require further review.)

**November 20 validation benchmarks for `sql/queries/q01`–`q08`:**

| Query | Analytical Focus | Expected Rows Returned |
|---|---|---:|
| `Q01` — Flood damage by year | Annual flood property loss trajectory | `66` |
| `Q02` — Flood frequency vs. severity | State-level frequency vs. severity decomposition | `6` |
| `Q03` — Hail seasonality | Seasonal hail exposure across target regions | `70` |
| `Q04` — Billion-dollar episodes | Catastrophic multi-billion-dollar storm episodes | `4` |
| `Q05` — Fatalities vs. damage | Under-counted property damage relative to mortality | `29` |
| `Q06` — County damage per capita | Per-capita and housing-adjusted county storm losses | `25` |
| `Q07` — Hurricane peak winds | Maximum sustained wind intensity by cyclone | `25` |
| `Q08` — Hurricane station proximity | Coastal station observations near cyclone tracks | `100` |

### 6. Check database storage against the 8 GB team budget

```sql
SELECT
    pg_size_pretty(SUM(pg_total_relation_size(c.oid))) AS team_size,
    ROUND((SUM(pg_total_relation_size(c.oid)) / (8.0 * 1024^3) * 100)::numeric, 2) AS pct_of_8gb_limit
FROM pg_class AS c
JOIN pg_namespace AS n
    ON n.oid = c.relnamespace
WHERE n.nspname = 'prancer'
  AND c.relkind IN ('r', 'm');
```

*Normal behavior:* Storage remains well under the **8 GB** per-team quota (including indexes). Avoid ingesting multi-decade nationwide GHCN windows when only the six-state Southeast region is needed.

---

## When something fails

| What you see | What it means | What to do |
|---|---|---|
| `ModuleNotFoundError: No module named 'course_db'` | Script was invoked outside the repo root or `.venv` is inactive | `cd` to the repository root, run `source .venv/bin/activate`, and verify `src/course_db.py` exists |
| CMU Entra authentication failure | Expired SSO token or missing `PGUSER` | Run `export PGUSER="YOUR_ANDREW_ID@andrew.cmu.edu"`, complete CMU Microsoft Entra sign-in, and retry |
| `Missing CENSUS_API_KEY environment variable.` | `--source census` ran without `CENSUS_API_KEY` set | Run `export CENSUS_API_KEY="your_key"` and re-execute |
| `Validation failed; nothing was loaded: negative precipitation` or `tmax below tmin` | Upstream `course.observations` contained invalid physical values | Transaction rolled back automatically; inspect bad rows in `course.observations`, log in `docs/technical-spec.md`, and rerun |
| `HURDAT2 integrity error on <storm_id>: expected <X> pts, saw <Y>` | NHC's `hurdat2` archive had a truncated storm record or partial download | Wait 1–2 minutes and rerun `--source hurdat`; no partial rows were committed |
| `requests.exceptions.HTTPError` or `ReadTimeout` (NWS / NOAA / Census) | Upstream federal API is temporarily throttled or unreachable | Wait 2–5 minutes and retry; cached `.csv.gz` files in `data/raw/storm_events/` are reused automatically |
| `relation "..." does not exist` | Wrong schema on `search_path` or table not yet created | Run `SET search_path = prancer, course, public;` and check `pg_tables` |
| `column does not exist` | Query and table definitions differ | Compare the SQL against current column definitions in `sql/schema.sql` |
| `duplicate key value violates unique constraint` | Staging rows conflicted with an existing primary/unique key | Inspect `ON CONFLICT` target columns in `src/refresh.py` against `sql/schema.sql` |
| `0 rows inserted, 0 updated` | Requested date window is already loaded and unchanged | Confirm `MAX(begin_ts)` / `MAX(date)` in target table; no action needed if current |
| Schema storage approaches **8 GB** | Large nationwide historical loads filled disk quota | Inspect per-table sizes with `pg_total_relation_size` and restrict unnecessary geographic scope |

> **Filesystem note:** While PostgreSQL rolls back all database changes on failure, downloaded `.csv.gz` files in `data/raw/storm_events/` remain cached on disk and will be reused on retry.

---

## Reports

### State-Level Flood Property Damage Growth (Frequency vs. Severity)

* **Client question:** Which states saw the biggest rise in flood property damage, and is that rise driven by how often floods happen (frequency) or how bad they are (severity)?
* **Built by:** `src/report.py`, which runs a parameterized query against `storm_events` (`event_type ILIKE '%Flood%'`) joined with `states` to compare event frequency (`Base_Cnt` vs. `Rec_Cnt`) and mean per-event severity (`Base_Avg($M)` vs. `Rec_Avg($M)`) across two 15-year windows (`1996-01-01`–`2011-01-01` vs. `2011-01-01`–`2026-09-01`).
* **Regenerate Command:**
  ```bash
  python src/report.py --team prancer
  ```
  *To filter to a single state (2-letter postal code or 2-digit FIPS) or customize comparison windows:*
  ```bash
  python src/report.py --team prancer --state TX --limit 10
  ```
* **When new data arrive:** NOAA Storm Events (`--source storms`) updates monthly. Because `src/report.py` binds `search_path` dynamically via `--team` and queries base tables directly, rerunning the command immediately incorporates newly loaded events with no intermediate views to rebuild.
* **Check after each refresh:** Confirm that top-ranked states align with historical catastrophic flood exposure (`TX` `+$47,036.22M` driven by `Severity`, `LA` `+$10,168.16M` driven by `Severity`, `NC` `+$2,889.04M` driven by `Severity`, and `FL` `+$1,039.37M` driven by `Frequency`).

---

## Recover

If a refresh fails or data becomes corrupted, follow these steps to restore a clean database state:

### 1. Identify the failing source

Read the terminal error message to determine whether the failure occurred during HTTP download, CSV/JSON parsing, staging validation (`run_checks()`), or `ON CONFLICT` upserts.

### 2. Verify the database connection

```bash
python src/course_db.py
```

Confirm `mads_f26` is reachable and your target schema tables are intact.

### 3. Check for partial changes

Every source in `src/refresh.py` executes inside `with conn.transaction():` using `ON COMMIT DROP` temporary tables. If an exception is raised, PostgreSQL automatically rolls back the entire transaction—previously committed rows remain untouched. Verify via the affected table's row count and `ingestion_runs`.

### 4. Resolve the root cause

* **Invalid source records:** Inspect the offending records in the upstream feed or cached `.csv.gz` file, adjust cleaning/validation logic if needed, and document the decision under Known Issues in `docs/technical-spec.md`.
* **Schema mismatch:** Compare live table columns against `sql/schema.sql`.
* **API or auth failure:** Verify network access, `CENSUS_API_KEY`, or CMU Entra sign-in (`PGUSER`).

### 5. Retry with a dry run

Test the fix without committing changes:

```bash
python src/refresh.py --team prancer --source ghcn --start 2025-09-01 --end 2025-10-01 --dry-run
```

Confirm it prints the staged counts followed by:

```text
Dry run: undoing all changes.
```

### 6. Run the actual refresh

Once the dry run succeeds, remove `--dry-run` to commit:

```bash
python src/refresh.py --team prancer --source ghcn --start 2025-09-01 --end 2025-10-01
```

*(If rebuilding an entire schema from scratch after authorization, update `SET ROLE` and `SET search_path` in `sql/schema.sql` to `vixen`, run `psql -d mads_f26 -v ON_ERROR_STOP=1 -f sql/schema.sql`, and reload sources in dependency order: `census` → `ghcn` → `storms` → `hurdat` → `nws`.)*

### 7. Verify recovery

Check row counts, date coverage, `ingestion_runs`, `sql/tests/t01`–`t08`, and `python src/report.py --team prancer`. Re-running the same refresh window should yield `0 inserted, 0 updated` with no duplicate records.

> **Caution:** Do not drop populated tables or rebuild the database without authorization.

---

## Who owns what

### Builders — Team Prancer

Team Prancer designed and built the Climate Risk Analytics system and is responsible for its original database schema, ingestion pipelines, client queries, validation tests, and handoff documentation.

| Component | Original Responsibility (Team Prancer) | Primary Files & Tables |
|---|---|---|
| **Database Architecture & Core Ingestion Pipeline** | Ainika Hou | `sql/schema.sql`, `src/refresh.py`, `states`, `counties`, `stations`, `observations`, `nws_observations`, `county_demographics`, `ingestion_runs` |
| **NOAA Storm Events & Hurricane Ingestion** | Matt Mellors | `src/refresh.py` (`--source storms`, `--source hurdat`), `storm_events`, `hurdat_storms`, `hurdat_tracks` |
| **Client SQL Queries & Validation Tests** | Bruck Setu | `sql/queries/q01`–`q08`, `sql/tests/t01`–`t08` |
| **Client CLI Report, Integration & Documentation** | Team Prancer collectively | `src/report.py`, `README.md`, `docs/technical-spec.md`, `docs/runbook.md` |

### Receivers — Team Vixen

**Team Vixen** assumes operational ownership of the Climate Risk Analytics system during the **November 23** knowledge-transfer session.

* **Post-handoff responsibilities:** Running scheduled refreshes (`--team vixen`), monitoring data quality and storage against the 8 GB budget, executing validation tests, and investigating upstream feed failures.
* **Design support & documentation:** Team Prancer will walk through architectural choices and known limitations during the November 23 handoff; Team Vixen should use `README.md`, `docs/technical-spec.md`, and this `docs/runbook.md` as the primary operational reference.
