from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from pregnancy_copilot.daily_consolidation import consolidate_day
from pregnancy_copilot.storage import PregnancyDataStore


def run_daily_consolidation(
    data_root: str | Path,
    date: str,
    ai_summary: str | None = None,
) -> dict:
    result = consolidate_day(PregnancyDataStore(Path(data_root)), date, ai_summary=ai_summary)
    return {
        "ok": True,
        "date": result.date,
        "message_count": result.message_count,
        "event_count": result.event_count,
        "daily_log_path": result.daily_log_path.as_posix(),
        "index_path": result.index_path.as_posix(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Consolidate one day of local Pregnancy Copilot memory.")
    parser.add_argument("--data-root", default="./pregnancy-data")
    parser.add_argument("--date", default=None, help="YYYY-MM-DD; defaults to today in Asia/Shanghai")
    parser.add_argument("--ai-summary", default=None, help="Optional host-LLM organized summary")
    args = parser.parse_args()
    date = args.date or datetime.now(timezone(timedelta(hours=8))).date().isoformat()
    print(json.dumps(run_daily_consolidation(args.data_root, date, args.ai_summary), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
