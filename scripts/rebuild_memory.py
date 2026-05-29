from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pregnancy_copilot.artifacts import generate_daily_log
from pregnancy_copilot.context_builder import build_current_context, build_emotional_pattern, build_medical_timeline
from pregnancy_copilot.daily_metrics import build_daily_metrics_index
from pregnancy_copilot.storage import PregnancyDataStore


def rebuild_memory(data_root: str | Path, date: str | None = None) -> dict[str, str]:
    store = PregnancyDataStore(Path(data_root))
    date = date or datetime.now(timezone(timedelta(hours=8))).date().isoformat()
    current_context = build_current_context(store)
    medical_timeline = build_medical_timeline(store)
    emotional_pattern = build_emotional_pattern(store)
    daily_metrics = build_daily_metrics_index(store)
    daily_log = generate_daily_log(store, date)
    return {
        "current_context": current_context.as_posix(),
        "medical_timeline": medical_timeline.as_posix(),
        "emotional_pattern": emotional_pattern.as_posix(),
        "daily_metrics": (store.root / "memory" / "daily_metrics.yaml").as_posix(),
        "daily_log": daily_log.as_posix(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", default="./pregnancy-data")
    parser.add_argument("--date", default=None, help="Date in YYYY-MM-DD. Defaults to today in Asia/Shanghai.")
    args = parser.parse_args()

    print(json.dumps(rebuild_memory(args.data_root, date=args.date), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
