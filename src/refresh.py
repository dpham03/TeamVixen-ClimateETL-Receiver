import argparse

from refresh_ghcn import refresh_ghcn_api
from refresh_storms import refresh_storms
from refresh_hurricanes import refresh_hurricanes
from refresh_nws import refresh_nws
from refresh_nws_alerts import refresh_nws_alerts
from refresh_census import refresh_census


def main():

    parser = argparse.ArgumentParser(
        description="Refresh the Prancer climate database"
    )

    parser.add_argument(
        "--source",
        choices=[
            "ghcn",
            "storms",
            "hurricanes",
            "nws",
            "nws_alerts",
            "census",
            "all"
        ],
        default="all"
    )

    args = parser.parse_args()

    if args.source in ("ghcn", "all"):
        print("\nRefreshing GHCN...")
        refresh_ghcn_api()

    if args.source in ("storms", "all"):
        print("\nRefreshing Storm Events...")
        refresh_storms()

    if args.source in ("hurricanes", "all"):
        print("\nRefreshing Hurricanes...")
        refresh_hurricanes()

    if args.source in ("nws", "all"):
        print("\nRefreshing NWS Observations...")
        refresh_nws()

    if args.source in ("nws_alerts", "all"):
        print("\nRefreshing NWS Alerts...")
        refresh_nws_alerts()

    if args.source in ("census", "all"):
        print("\nRefreshing Census Demographics...")
        refresh_census()

    print("\nRefresh complete!")


if __name__ == "__main__":
    main()