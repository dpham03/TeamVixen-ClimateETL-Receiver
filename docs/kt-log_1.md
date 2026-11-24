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
| C2. Table creation, row units, keys, and constraints | Y | complete | high | moderate | C1 | 4 | 4 | Nov 23, 2026 |
| C3. Spatial join keys and enrichment joins | Y | complete | high | high | C1 | 2 | 2 | Nov 23, 2026 |
| **D. Pipeline** | | | | | | | | |
| D1. Connecting: CMU sign-in, team role, and `course_db.py` | Y | complete | high | low | none | 2 | 2 | Nov 23, 2026 |
| D2. Refresh files, granular refresh, date ranges, and runbook — led by Matt | Y | complete | high | high | D1, B | 5 | 5 | Nov 23, 2026 |
| D3. Staging and validation checks | Y | complete | high | moderate | D2 | 2 | 2 | Nov 23, 2026 |
| D4. Merge and rerun safety | Y | complete | high | high | D3 | 2 | 2 | Nov 23, 2026 |
| D5. Run log (`ingestion_runs`) | Y | complete | moderate | low | D2 | 1 | 1 | Nov 23, 2026 |
| **E. Queries and reports** | | | | | | | | |
| E1. Client SQL queries and their relevance to the core questions — led by Bruck | Y | complete | high | moderate | C | 5 | 5 | Nov 23, 2026 |
| E2. The Python report command | Y | complete | moderate | moderate | D1 | 2 | 2 | Nov 23, 2026 |
| **F. What if?** | | | | | | | | |
| F1. Refresh failures, long runtimes, and narrower date ranges | Y | complete | high | moderate | D | 2 | 2 | Nov 23, 2026 |
| F2. A source is down or changes its format | Y | complete | moderate | high | B, D | 1 | 1 | Nov 23, 2026 |
| F3. Validation rejects rows | Y | complete | high | moderate | D3 | 1 | 1 | Nov 23, 2026 |
| F4. The source revises data already loaded | Y | complete | moderate | moderate | D4 | 1 | 1 | Nov 23, 2026 |
| **G. Quality checks** | | | | | | | | |
| G1. Run the tests in `sql/tests/` | Y | complete | high | moderate | E1 | 2 | 2 | Nov 23, 2026 |
| G2. Check row counts and date coverage after a refresh | Y | complete | high | low | D2 | 1 | 1 | Nov 23, 2026 |
| G3. Reproduce one documented result | Y | complete | high | moderate | E1 | 1 | 1 | Nov 23, 2026 |
| **Total** | | | | | | **50** | **50** | |

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
