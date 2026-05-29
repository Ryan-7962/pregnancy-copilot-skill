from __future__ import annotations

import argparse
import json
from pathlib import Path

from pregnancy_copilot.adapters.feishu_mock import MockFeishuAdapter
from pregnancy_copilot.event_processor import process_feishu_event
from pregnancy_copilot.storage import PregnancyDataStore
try:
    from scripts.init_data_dir import initialize_data_dir
except ModuleNotFoundError:
    from init_data_dir import initialize_data_dir


def run_install_check(data_root: str | Path) -> dict:
    root = Path(data_root)
    initialize_data_dir(root)
    store = PregnancyDataStore(root)
    adapter = MockFeishuAdapter()
    event = process_feishu_event(
        {
            "event_id": "install-check-001",
            "message_id": "install-check-message-001",
            "timestamp": "2026-05-05T09:00:00+08:00",
            "sender_id": "install-check-user",
            "chat_id": "install-check-chat",
            "chat_type": "p2p",
            "content": "今天肚子有点紧，休息后好了，没有流血也没有流水",
            "message_type": "text",
        },
        store=store,
        adapter=adapter,
    )
    date = event["timestamp"][:10]
    raw_message = root / "inbox" / "raw_feishu_messages" / f"{date}.md"
    events = root / "events" / "events.jsonl"
    current_context = root / "memory" / "current_context.md"
    medical_timeline = root / "memory" / "medical_timeline.md"
    emotional_pattern = root / "memory" / "emotional_pattern.md"
    daily_log = root / "daily_logs" / f"{date}.md"
    return {
        "ok": all(path.exists() for path in [raw_message, events, current_context, medical_timeline, emotional_pattern, daily_log])
        and bool(adapter.sent_replies),
        "risk_level": event["risk_level"],
        "raw_message": raw_message.as_posix(),
        "events": events.as_posix(),
        "current_context": current_context.as_posix(),
        "medical_timeline": medical_timeline.as_posix(),
        "emotional_pattern": emotional_pattern.as_posix(),
        "daily_log": daily_log.as_posix(),
        "reply": adapter.sent_replies[-1][1] if adapter.sent_replies else "",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", default="/tmp/pregnancy-copilot-install-check")
    args = parser.parse_args()

    result = run_install_check(args.data_root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
