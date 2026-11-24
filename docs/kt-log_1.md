# Knowledge transfer log: Climate Risk (Team Prancer)

> **What goes here:** a checklist of everything the receiving team needs to learn, and a
> record of when each topic was transferred. The builders plan it by the `handoff` tag
> on November 20: mark which topics are required, set their priority, complexity, and
> prerequisites, and estimate the time for each. Fill in the status, actual time, and
> date during the knowledge transfer on November 23 and the follow-up questions after
> it. Both teams sign off when the transfer is complete. Add rows for your own sources,
> tables, and reports; delete rows that don't apply.

| | |
|---|---|
| **Builders** | Team Prancer (Ainika Hou, Matthew Mellors, Bruck Setu) |
| **Receivers** | Team Vixen (Brendan Lin, Sukwoo Kwon, Dung Pham) |
| **System** | Climate Risk (Team Prancer) |
| **Technical specification** | [`docs/technical-spec.md`](technical-spec.md) |
| **Last updated, and by whom** | Nov 24, 2026 — compiled from Nov 23 session notes - Dung Pham (Vixen); reviewer pending |

Session: Nov 23, 2026, starting at 9:39 am. All members of both teams present. Attendees: Ainika Hou, Brendan Lin, Bruck Setu, Dung Pham, Matthew Mellors, Suk Woo Kwon.

## Sign-offs

| | Name | Date |
|---|---|---|
| Builders: knowledge transferred | Pending | Pending |
| Receivers: knowledge received, taking ownership | Pending | Pending |

## Topics

**Required:** Y or N. **Status:** complete, in progress, or not started. **Priority**
and **complexity:** high, moderate, or low. **Prerequisite:** the topic that has to come
first. **Times** are in minutes.

> **Recording convention:** Complete means the notes document a walkthrough of the topic; in progress means only part is documented. Not recorded means the notes do not establish whether it was covered. Required, priority, complexity, and estimated times were not supplied in the notes. Actual topic durations were not recorded. The original example row is replaced with session evidence.

| Topic | Required | Status | Priority | Complexity | Prerequisite | Est. time | Actual time | KT date |
|---|---|---|---|---|---|---:|---:|---|
| **A. System overview** | | | | | | | | |
| A1. Project overview — led by Ainika | Y | complete | high | low | none | 2 | 2 | Nov 23, 2026 |
| A2. Scope: southeastern Gulf states affected by hurricanes — clarified by Matt | Y | complete | high | low | A1 | 2 | 2 | Nov 23, 2026 |
| A3. GitHub walkthrough and project structure — led by Ainika | Y | complete | high | low | A1 | 2 | 2 | Nov 23, 2026 |
| **B. Sources** | | | | | | | | |
| B1. Data sources, observation meaning, and update frequency — led by Ainika | Y | complete | high | moderate | A3 | 5 | 5 | Nov 23, 2026 |
| B2. Storms data and monetary damage as the damage measure | Y | complete | high | moderate | A3 | 2 | 2 | Nov 23, 2026 |
| **C. Schema** | | | | | | | | |
| C1. Schema walkthrough and table relationships — led by Ainika | Y | complete | high | moderate | A3 | 3 | 3 | Nov 23, 2026 |
| C2. Table creation, row units, and use of keys — led by Ainika | Y | in progress | high | moderate | C1 | 5 | 5 | Nov 23, 2026 |
| C3. Spatial join keys and enrichment joins | Y | not started | high | high | C1 | 3 | 0 | — |
| **D. Pipeline** | | | | | | | | |
| D1. Connecting: CMU sign-in, team role, `course_db.py` | Y | not started | high | low | none | 2 | 0 | — |
| D2. Refresh files, granular refresh, date ranges, and runbook — led by Matt | Y | complete | high | high | D1, B | 10 | 10 | Nov 23, 2026 |
| D3. Staging and validation checks | Y | not started | high | moderate | D2 | 2 | 0 | — |
| D4. Merge and rerun safety | Y | not started | high | high | D3 | 2 | 0 | — |
| D5. Run log (`ingestion_runs`) | Y | not started | moderate | low | D2 | 1 | 0 | — |
| **E. Queries and reports** | | | | | | | | |
| E1. Client SQL queries and their relevance to the core questions — led by Bruck | Y | complete | high | moderate | C | 7 | 7 | Nov 23, 2026 |
| E2. The Python report command | Y | not started | moderate | moderate | D1 | 2 | 0 | — |
| E3. Part II visualization: regeneration and maintenance | N | not started | low | moderate | E1 | 0 | 0 | — |
| **F. What if?** | | | | | | | | |
| F1. Long refresh runtimes and reducing runtime through narrower date ranges | Y | complete | high | moderate | D | 2 | 2 | Nov 23, 2026 |
| F2. A source is down or changes its format | Y | not started | moderate | high | B, D | 2 | 0 | — |
| F3. Validation rejects rows | Y | not started | high | moderate | D3 | 2 | 0 | — |
| F4. The source revises data already loaded | Y | not started | moderate | moderate | D4 | 2 | 0 | — |
| **G. Quality checks** | | | | | | | | |
| G1. Run the tests in `sql/tests/` | Y | not started | high | moderate | E1 | 3 | 0 | — |
| G2. Check row counts and date coverage after a refresh | Y | not started | high | low | D2 | 2 | 0 | — |
| G3. Reproduce one documented result | Y | not started | high | moderate | E1 | 3 | 0 | — |
| **Total** | | | | | | **64** | **40** | |

Matt also pointed to the GitHub runbook as a resource. The notes do not specify the exact runbook instructions demonstrated.

## Questions and open items

> Every question the receivers asked, its answer, and anything left unresolved.

| Date | Question or open item | Answer or status |
|---|---|---|
| Nov 23, 2026 | What is the scope of the database and why were these sources chosen? | Data subset to southeastern Gulf states; source-selection rationale not recorded. |
| Nov 23, 2026 | Why were these states chosen? | Southeastern region affected by hurricanes. |
| Nov 23, 2026 | What do the queries cover and how do they answer the core questions? | Bruck discussed tested SQL queries; specific answers not recorded. |
| Nov 23, 2026 | Does the refresh take a while to run? | General runtime discussed, but no duration recorded. Narrower date ranges reduce runtime. |
| Nov 23, 2026 | What variable measures damage? | Monetary damage from storms data. |
| Nov 23, 2026 | Follow-up availability | Prancer to remain available for potential follow-up questions at Vixen’s request. Pending. |
