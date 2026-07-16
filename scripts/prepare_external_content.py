#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path

from pregnancy_copilot.external_content.runtime import prepare_external_content_action


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a Xiaohongshu post for host-Agent audit.")
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--captured-at", default=datetime.now().astimezone().isoformat())
    parser.add_argument("--question")
    parser.add_argument("--no-record", action="store_true")
    parser.add_argument("--video-policy", choices=("ask", "always", "never"), default="ask")
    parser.add_argument("--video-consent", action="store_true")
    args = parser.parse_args()
    action = prepare_external_content_action(
        args.data_root,
        url=args.url,
        captured_at=args.captured_at,
        user_question=args.question,
        record_mode="no_record" if args.no_record else "default",
        video_policy=args.video_policy,
        video_consent=args.video_consent,
    )
    print(json.dumps(action, ensure_ascii=False, indent=2))
    return 0 if action.get("status") == "ready_for_host_analysis" else 2


if __name__ == "__main__":
    raise SystemExit(main())
