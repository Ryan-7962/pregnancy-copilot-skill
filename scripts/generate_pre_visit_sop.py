from __future__ import annotations

import argparse
from pathlib import Path

from pregnancy_copilot.storage import PregnancyDataStore
from pregnancy_copilot.visit_sop import generate_pre_visit_sop


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a pre-visit doctor discussion SOP.")
    parser.add_argument("--data-root", default="./pregnancy-data")
    parser.add_argument("--date", required=True, help="Visit date, YYYY-MM-DD.")
    parser.add_argument("--lookback-days", type=int, default=14)
    args = parser.parse_args()

    path = generate_pre_visit_sop(
        PregnancyDataStore(Path(args.data_root)),
        visit_date=args.date,
        lookback_days=args.lookback_days,
    )
    print(path)


if __name__ == "__main__":
    main()
