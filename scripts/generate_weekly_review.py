from __future__ import annotations

import argparse
from datetime import date, timedelta

from pregnancy_copilot.artifacts import write_weekly_artifacts
from pregnancy_copilot.storage import PregnancyDataStore


def default_week_range(today: date | None = None) -> tuple[str, str]:
    today = today or date.today()
    start = today - timedelta(days=6)
    return start.isoformat(), today.isoformat()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate weekly review and baby weekly diary.")
    parser.add_argument("--data-root", default="./pregnancy-data")
    parser.add_argument("--start-date", help="Inclusive start date, YYYY-MM-DD. Defaults to recent 7 days.")
    parser.add_argument("--end-date", help="Inclusive end date, YYYY-MM-DD. Defaults to today.")
    args = parser.parse_args()

    start_date, end_date = (args.start_date, args.end_date) if args.start_date and args.end_date else default_week_range()
    result = write_weekly_artifacts(PregnancyDataStore(args.data_root), start_date, end_date)
    print(f"Weekly review: {result['weekly_review_path']}")
    print(f"Baby diary: {result['baby_diary_path']}")


if __name__ == "__main__":
    main()
