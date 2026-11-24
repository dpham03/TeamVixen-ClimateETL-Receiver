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
| A1. Project overview — led by Ainika | Not recorded | complete | Not recorded | Not recorded | none | Not recorded | Not recorded | Nov 23, 2026 |
| A2. Scope: southeastern Gulf states affected by hurricanes — clarified by Matt | Not recorded | complete | Not recorded | Not recorded | A1 | Not recorded | Not recorded | Nov 23, 2026 |
| A3. GitHub walkthrough — led by Ainika; full source-to-report flow not recorded | Not recorded | in progress | Not recorded | Not recorded | A1 | Not recorded | Not recorded | Nov 23, 2026 |
| **B. Sources** | | | | | | | | |
| B1. Data sources: observation meaning and update frequency — led by Ainika; source-specific details not recorded | Not recorded | complete | Not recorded | Not recorded | A3 | Not recorded | Not recorded | Nov 23, 2026 |
| B2. Storms data: monetary damage used as the damage measure | Not recorded | in progress | Not recorded | Not recorded | A3 | Not recorded | Not recorded | Nov 23, 2026 |
| **C. Schema** | | | | | | | | |
| C1. Schema walkthrough: tables and keys — led by Ainika; ER diagram not explicitly recorded | Not recorded | in progress | Not recorded | Not recorded | A3 | Not recorded | Not recorded | Nov 23, 2026 |
| C2. Table creation and use of keys — led by Ainika; individual row units and constraints not recorded | Not recorded | in progress | Not recorded | Not recorded | C1 | Not recorded | Not recorded | Nov 23, 2026 |
| C3. Spatial join keys and enrichment joins | Not recorded | Not recorded | Not recorded | Not recorded | C1 | Not recorded | Not recorded | Not recorded |
| **D. Pipeline** | | | | | | | | |
| D1. Connecting: CMU sign-in, team role, `course_db.py` | Not recorded | Not recorded | Not recorded | Not recorded | none | Not recorded | Not recorded | Not recorded |
| D2. Refresh files and functionality — led by Matt; granular refresh and narrower date ranges discussed | Not recorded | complete | Not recorded | Not recorded | D1, B | Not recorded | Not recorded | Nov 23, 2026 |
| D3. Staging and validation checks | Not recorded | Not recorded | Not recorded | Not recorded | D2 | Not recorded | Not recorded | Not recorded |
| D4. Merge and rerun safety | Not recorded | Not recorded | Not recorded | Not recorded | D3 | Not recorded | Not recorded | Not recorded |
| D5. Run log (`ingestion_runs`) | Not recorded | Not recorded | Not recorded | Not recorded | D2 | Not recorded | Not recorded | Not recorded |
| **E. Queries and reports** | | | | | | | | |
| E1. SQL queries tested against core client questions — discussed by Bruck; individual queries and test results not recorded | Not recorded | in progress | Not recorded | Not recorded | C | Not recorded | Not recorded | Nov 23, 2026 |
| E2. The Python report command | Not recorded | Not recorded | Not recorded | Not recorded | D1 | Not recorded | Not recorded | Not recorded |
| E3. [Part II visualization]: how to regenerate and maintain it | Not recorded | Not recorded | Not recorded | Not recorded | E1 | Not recorded | Not recorded | Not recorded |
| **F. What if?** | | | | | | | | |
| F1. A refresh fails partway | Not recorded | Not recorded | Not recorded | Not recorded | D | Not recorded | Not recorded | Not recorded |
| F2. A source is down or changes its format | Not recorded | Not recorded | Not recorded | Not recorded | B, D | Not recorded | Not recorded | Not recorded |
| F3. Validation rejects rows | Not recorded | Not recorded | Not recorded | Not recorded | D3 | Not recorded | Not recorded | Not recorded |
| F4. The source revises data already loaded | Not recorded | Not recorded | Not recorded | Not recorded | D4 | Not recorded | Not recorded | Not recorded |
| **G. Quality checks** | | | | | | | | |
| G1. Run the tests in `sql/tests/` | Not recorded | Not recorded | Not recorded | Not recorded | E1 | Not recorded | Not recorded | Not recorded |
| G2. Check row counts and date coverage after a refresh | Not recorded | Not recorded | Not recorded | Not recorded | D2 | Not recorded | Not recorded | Not recorded |
| G3. Reproduce one documented result | Not recorded | Not recorded | Not recorded | Not recorded | E1 | Not recorded | Not recorded | Not recorded |

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
