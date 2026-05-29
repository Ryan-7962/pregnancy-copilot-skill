from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pregnancy_copilot.artifacts import generate_daily_log
from pregnancy_copilot.storage import PregnancyDataStore


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", default="./pregnancy-data")
    parser.add_argument("--date", default=None, help="Date in YYYY-MM-DD. Defaults to today in Asia/Shanghai.")
    args = parser.parse_args()

    date = args.date or datetime.now(timezone(timedelta(hours=8))).date().isoformat()
    path = generate_daily_log(PregnancyDataStore(Path(args.data_root)), date)
    print(f"Daily log: {path}")


if __name__ == "__main__":
    main()
