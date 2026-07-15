from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone

from pregnancy_copilot.migration_v021 import migrate_to_v021


def main() -> None:
    parser = argparse.ArgumentParser(description="Back up and migrate Pregnancy Copilot data from v0.2.0 to v0.2.1.")
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--date", help="YYYY-MM-DD; defaults to today in Asia/Shanghai.")
    args = parser.parse_args()
    date = args.date or datetime.now(timezone(timedelta(hours=8))).date().isoformat()
    result = migrate_to_v021(args.data_root, date=date)
    payload = {**result, "backup_path": str(result["backup_path"]), "report_path": str(result["report_path"])}
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
