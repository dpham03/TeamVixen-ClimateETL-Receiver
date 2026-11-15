# Climate Risk Analytics & P&C Insurance Underwriting · Team Prancer

## What this system is for

This PostgreSQL system supports a property and casualty (P&C) firm's insurance underwriting and exposure team. It helps figure out how much to charge for policies in areas with different weather risks, decide when and where to allocate extra claims adjusters during busy storm seasons, and identify which specific weather patterns lead to the most expensive flood and storm payouts due to damage. To do this, it integrates historical NOAA storm events (1996-2026), NHC HURDAT2 Atlantic hurricane tracks (1980-2025), GHCN-Daily weather station logs, live NWS observations and alerts, and 2024 U.S. Census ACS 5-year county demographics; these are joined on county FIPS codes. It does not cover proprietary policy-level claims, Zillow typical home values, or satellite building-damage imagery.

## Start here

*The first commands a receiving team should run, in order, with what each one should
print. Example:*

1. `python3.13 -m venv .venv` and `.venv/bin/python -m pip install -r requirements.txt`,
   then select the `.venv` interpreter in VS Code. The install should end with
   "Successfully installed …".
2. `export PGUSER="andrewid@andrew.cmu.edu"` and `python src/course_db.py`. It should
   print "Connected to mads_f26 as …".
3. `python src/refresh.py --team prancer --start 2025-09-01 --end 2025-10-01 --dry-run`.
   It should report how many rows it would insert and update, then undo everything.
4. `python src/report.py --team prancer --state PA --start 2025-09-01 --end 2025-10-01`.
   It should print a table of stations.

## What's in the handoff pack

| Piece | Where |
|---|---|
| **README:** where to start | this file |
| **Technical specification:** overview and scope, process-flow and ER diagrams, sources, every table, program, and query, design decisions, known issues | `docs/technical-spec.md` |
| **Runbook:** connect, refresh, check, recover, and use and maintain the reports | `docs/runbook.md` |
| **The code:** schema, refresh, client queries and their tests, Python command, report, Python packages | `sql/schema.sql`, `src/refresh.py`, `sql/queries/`, `sql/tests/`, `src/report.py`, `reports/report.qmd`, `requirements.txt` |
| **AI log** | `ai/AI-LOG.md` |
| **Knowledge transfer plan:** topics, required or not, priority, complexity, prerequisites, estimated times | `docs/kt-log.md` |

`docs/kt-log.md` is the knowledge transfer log: plan it by the `handoff` tag on November
20, and fill it in during the knowledge transfer on November 23.

`src/course_db.py` connects to the course server with your CMU sign-in; don't edit it.
`receiver/` stays empty until the handoff; the receiving team works there.

## Rules for this repository

- **No credentials, ever:** no passwords, tokens, or connection strings with secrets,
  including in old commits. `course_db.py` signs in with your CMU account, so you never
  need one.
- Raw downloads go in `data/raw/`, which Git ignores. The refresh step must be able to
  fetch them again.
- **Work as your team.** Before you create anything, switch to your team role. Tables
  created without it belong to you personally and won't transfer at the handoff.

  ```sql
  SET ROLE prancer_write;
  SET search_path = prancer, course, public;
  ```

  In Python, `course_db.connect(team="prancer")` does both.
- **Name everything in lowercase snake_case**, such as `begin_yearmonth` or
  `ev_level2_evse_num`. PostgreSQL lowercases names that aren't in double quotes, so a
  column created as `BEGIN_YEARMONTH` or `EV Level2 EVSE Num` can only be queried with
  the double quotes, every time. `df.to_sql()` keeps a file's headers exactly as they
  are, so clean them before loading:

  ```python
  df.columns = df.columns.str.lower().str.replace(r"[^a-z0-9]+", "_", regex=True)
  ```
