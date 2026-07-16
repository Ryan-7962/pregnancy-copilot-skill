from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json

from pregnancy_copilot.migration_v030 import migrate_to_v030


def main() -> None:
    parser = argparse.ArgumentParser(description="Back up and migrate Pregnancy Copilot data from v0.2.1 to v0.3.0.")
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--date", help="YYYY-MM-DD; defaults to today in Asia/Shanghai")
    args = parser.parse_args()
    date = args.date or datetime.now(timezone(timedelta(hours=8))).date().isoformat()
    result = migrate_to_v030(args.data_root, date=date)
    payload = {
        **result,
        "backup_path": str(result["backup_path"]),
        "daily_index_path": str(result["daily_index_path"]),
        "report_path": str(result["report_path"]),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
