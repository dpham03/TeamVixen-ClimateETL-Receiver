"""Report: a client query that takes parameters.

    python src/report.py 
    python src/report.py --team prancer --state TX
    python src/report.py --team prancer --baseline-start 1996-01-01 --baseline-end 2011-01-01  \
                         --recent-start 2011-01-01 --recent-end 2026-09-01

State-level flood property damage growth over time, looking at 
both frequency (number of events) and severity.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date

from course_db import connect

QUERY = """
    WITH flood_periods AS (
        SELECT
            s.state_abbr, 
            s.state_name, 
            CASE
                WHEN e.begin_ts >= %(baseline_start)s AND e.begin_ts < %(baseline_end)s THEN 'baseline'
                WHEN e.begin_ts >= %(recent_start)s AND e.begin_ts < %(recent_end)s THEN 'recent'
                END AS period, 
                COALESCE (e.damage_property_usd, 0) AS damage_usd
        FROM prancer.storm_events as e
        JOIN prancer.states as s
            ON e.state_fips = s.state_fips
        WHERE e.event_type ILIKE '%%Flood%%'
            AND (
                (e.begin_ts >= %(baseline_start)s AND e.begin_ts < %(baseline_end)s)
                OR (e.begin_ts >= %(recent_start)s AND e.begin_ts < %(recent_end)s)
            )
            AND (
                CAST(%(state)s AS TEXT) IS NULL
                OR s.state_abbr = %(state)s
                OR s.state_fips = %(state)s
            )
    ),
    aggregated AS (
        SELECT
            state_abbr,
            state_name,
            COUNT(*) FILTER (WHERE period = 'baseline') AS base_events,
            COUNT(*) FILTER (WHERE period = 'recent')   AS recent_events,
            COALESCE(SUM(damage_usd) FILTER (WHERE period = 'baseline'), 0) AS base_damage,
            COALESCE(SUM(damage_usd) FILTER (WHERE period = 'recent'), 0)   AS recent_damage
        FROM flood_periods
        GROUP BY state_abbr, state_name
    )
    SELECT
        state_abbr AS state,
        state_name,
        base_events,
        recent_events,
        ROUND(
            100.0 * (recent_events - base_events) / NULLIF(base_events, 0), 1
        ) AS freq_chg_pct,
        ROUND((base_damage / NULLIF(base_events, 0)) / 1e6, 2) AS base_avg_m,
        ROUND((recent_damage / NULLIF(recent_events, 0)) / 1e6, 2) AS recent_avg_m,
        ROUND((recent_damage - base_damage) / 1e6, 2) AS total_dmg_diff_m,
        CASE
            WHEN recent_damage <= base_damage THEN 'No Rise'
            WHEN COALESCE(1.0 * recent_events / NULLIF(base_events, 0), 0)
                    >= COALESCE((recent_damage / NULLIF(recent_events, 0))
                    / NULLIF(base_damage / NULLIF(base_events, 0), 0), 0)
            THEN 'Frequency'
            ELSE 'Severity'
        END AS primary_driver
    FROM aggregated
    WHERE base_events > 0 OR recent_events > 0
    ORDER BY (recent_damage - base_damage) DESC, state_abbr
    LIMIT %(limit)s;
"""


def parse_args() -> argparse.Namespace:
    """Define and parse command line args for the query."""
    parser = argparse.ArgumentParser(
        description="Analyze state-level flood property damage growth: frequency vs. severity."
    )
    # team can change
    parser.add_argument("--team", default="prancer", help="PostgreSQL team/schema")
    # single state in data base
    parser.add_argument("--state", default=None, help="Optional 2-letter postal code or 2-digit FIPS")
    # validates date YYYY-MM-DD format
    parser.add_argument(
        "--baseline-start",  # start of baseline period
        type=date.fromisoformat,
        default=date(1996, 1, 1),
        help="Baseline window start date, YYYY-MM-DD (default: 1996-01-01)",
    )
    parser.add_argument(
        "--baseline-end",  # end of baseline period
        type=date.fromisoformat,
        default=date(2011, 1, 1),
        help="Baseline window exclusive end date, YYYY-MM-DD (default: 2011-01-01)",
    )
    parser.add_argument(
        "--recent-start",  # start of recent period
        type=date.fromisoformat,
        default=date(2011, 1, 1),
        help="Recent window start date, YYYY-MM-DD (default: 2011-01-01)",
    )
    parser.add_argument(
        "--recent-end",  # end of recent period
        type=date.fromisoformat,
        default=date(2026, 9, 1),
        help="Recent window exclusive end date, YYYY-MM-DD (default: 2026-09-01)",
    )
    parser.add_argument("--limit", type=int, default=15, help="Max rows to display (default: 15)")
    return parser.parse_args()


def normalize_state(state_arg: str | None) -> str | None:
    """Standardize user state input to treat state abbr. or fips codes universally."""
    if not state_arg or not state_arg.strip():
        return None
    cleaned = state_arg.strip().upper()
    if cleaned.isdigit() and len(cleaned) <= 2:
        return cleaned.zfill(2)
    return cleaned


def format_table(headers: list[str], rows: list[tuple]) -> str:
    """create actual table for readability in terminal
    ==> this is an ASCII box
    """
    str_rows = [[str(val) if val is not None else "N/A" for val in row] for row in rows]
    widths = [
        max(len(headers[i]), *(len(r[i]) for r in str_rows))
        for i in range(len(headers))
    ]
    sep = "+-" + "-+-".join("-" * w for w in widths) + "-+"
    header_line = "| " + " | ".join(headers[i].ljust(widths[i]) for i in range(len(headers))) + " |"
    body_lines = [
        "| " + " | ".join(r[i].ljust(widths[i]) for i in range(len(headers))) + " |"
        for r in str_rows
    ]
    return "\n".join([sep, header_line, sep, *body_lines, sep])


def main() -> None:
    """Validate inputs from command line, execute query with parameters, and print results."""
    args = parse_args()
    if args.baseline_end <= args.baseline_start:
        raise ValueError("--baseline-end must be after --baseline-start")
    if args.recent_end <= args.recent_start:
        raise ValueError("--recent-end must be after --recent-start")

    params = {
        "state": normalize_state(args.state),
        "baseline_start": args.baseline_start,
        "baseline_end": args.baseline_end,
        "recent_start": args.recent_start,
        "recent_end": args.recent_end,
        "limit": args.limit,
    }

    # to help connect to team schema
    with connect(team=args.team) as conn:
        with conn.cursor() as cur:
            cur.execute(QUERY, params)
            rows = cur.fetchall()

    if not rows:
        print("No flood events matched the given filters.")
        sys.exit(0)

    headers = [
        "State",
        "Name",
        "Base_Ct",
        "Rec_Ct",
        "Freq_Chg%",
        "Base_Avg($M)",
        "Rec_Avg($M)",
        "Dmg_Diff($M)",
        "Driver",
    ]
    print(format_table(headers, rows))


if __name__ == "__main__":
    main()
