#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime
import json

from pregnancy_copilot.migration_v040 import migrate_to_v040


def main() -> None:
    parser = argparse.ArgumentParser(description="Back up and migrate Pregnancy Copilot data to v0.4.0.")
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--date")
    args = parser.parse_args()
    result = migrate_to_v040(args.data_root, args.date or datetime.now().astimezone().date().isoformat())
    print(
        json.dumps(
            {
                **result,
                "backup_path": str(result["backup_path"]),
                "external_index_path": str(result["external_index_path"]),
                "report_path": str(result["report_path"]),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
