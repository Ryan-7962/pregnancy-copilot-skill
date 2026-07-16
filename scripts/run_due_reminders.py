from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from pregnancy_copilot.prenatal_plan import claim_due_reminder_actions
from pregnancy_copilot.storage import PregnancyDataStore


def run_due_reminders(data_root: str | Path, date: str) -> dict:
    actions = claim_due_reminder_actions(PregnancyDataStore(Path(data_root)), date)
    return {"ok": True, "date": date, "action_count": len(actions), "actions": actions}


def main() -> None:
    parser = argparse.ArgumentParser(description="Claim due Pregnancy Copilot reminder actions for the host Agent.")
    parser.add_argument("--data-root", default="./pregnancy-data")
    parser.add_argument("--date", default=None, help="YYYY-MM-DD; defaults to today in Asia/Shanghai")
    args = parser.parse_args()
    date = args.date or datetime.now(timezone(timedelta(hours=8))).date().isoformat()
    print(json.dumps(run_due_reminders(args.data_root, date), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
