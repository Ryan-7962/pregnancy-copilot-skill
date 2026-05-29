from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pregnancy_copilot.backup import create_upgrade_backup


def create_backup_from_args(data_root: str | Path, target_version: str, date: str | None = None) -> Path:
    backup_date = date or datetime.now(timezone(timedelta(hours=8))).date().isoformat()
    return create_upgrade_backup(data_root, target_version=target_version, date=backup_date)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", default="./pregnancy-data")
    parser.add_argument("--target-version", required=True)
    parser.add_argument("--date", default=None, help="Date in YYYY-MM-DD. Defaults to today in Asia/Shanghai.")
    args = parser.parse_args()

    backup_path = create_backup_from_args(args.data_root, target_version=args.target_version, date=args.date)
    print(f"Backup: {backup_path}")


if __name__ == "__main__":
    main()
