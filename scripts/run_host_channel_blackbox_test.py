from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.evaluate_host_channel_blackbox import evaluate_host_channel_blackbox


DEFAULT_CHAT_ID = os.environ.get("PREGNANCY_COPILOT_TEST_CHAT_ID", "")


def build_send_command(chat_id: str, case_id: str, message: str) -> list[str]:
    return [
        "lark-cli",
        "im",
        "+messages-send",
        "--as",
        "user",
        "--chat-id",
        chat_id,
        "--text",
        f"[{case_id}] {message}",
    ]


def build_fetch_command(chat_id: str, page_size: int) -> list[str]:
    return [
        "lark-cli",
        "im",
        "+chat-messages-list",
        "--as",
        "user",
        "--chat-id",
        chat_id,
        "--page-size",
        str(page_size),
        "--sort",
        "desc",
        "--format",
        "json",
    ]


def load_case_messages(cases_path: str | Path, case_ids: list[str] | None = None) -> list[dict[str, str]]:
    selected = set(case_ids or [])
    payload = json.loads(Path(cases_path).read_text(encoding="utf-8"))
    cases = payload["cases"]
    if selected:
        cases = [case for case in cases if case["id"] in selected]
    return [{"id": case["id"], "message": case["message"]} for case in cases]


def send_cases(cases_path: str | Path, chat_id: str, delay_seconds: int, case_ids: list[str] | None = None) -> None:
    cases = load_case_messages(cases_path, case_ids=case_ids)
    for index, case in enumerate(cases):
        subprocess.run(build_send_command(chat_id, case["id"], case["message"]), check=True)
        if index != len(cases) - 1 and delay_seconds > 0:
            time.sleep(delay_seconds)


def fetch_messages(chat_id: str, output_path: str | Path, page_size: int) -> None:
    result = subprocess.run(build_fetch_command(chat_id, page_size), check=True, text=True, capture_output=True)
    Path(output_path).write_text(result.stdout, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Send, fetch, and evaluate host Agent channel pregnancy copilot blackbox cases.")
    parser.add_argument("--chat-id", default=DEFAULT_CHAT_ID)
    parser.add_argument("--cases", default="examples/host_channel_blackbox_cases.json")
    parser.add_argument("--case-id", action="append", dest="case_ids")
    parser.add_argument("--messages-output", default="/tmp/pregnancy-copilot-host-channel-blackbox-messages.json")
    parser.add_argument("--page-size", type=int, default=80)
    parser.add_argument("--delay-seconds", type=int, default=75)
    parser.add_argument("--send", action="store_true")
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--evaluate", action="store_true")
    args = parser.parse_args()

    if (args.send or args.fetch) and not args.chat_id:
        parser.error("--chat-id is required for --send/--fetch, or set PREGNANCY_COPILOT_TEST_CHAT_ID.")

    if args.send:
        send_cases(args.cases, args.chat_id, args.delay_seconds, case_ids=args.case_ids)
    if args.fetch:
        fetch_messages(args.chat_id, args.messages_output, args.page_size)
    if args.evaluate:
        result = evaluate_host_channel_blackbox(args.cases, args.messages_output)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if not result["ok"]:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
