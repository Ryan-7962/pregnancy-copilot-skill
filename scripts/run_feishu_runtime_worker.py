from __future__ import annotations

import argparse
import sys
import subprocess
import time
from collections.abc import Sequence
from pathlib import Path

from pregnancy_copilot.feishu_runtime_worker import (
    load_seen_message_ids,
    parse_chat_messages_list,
    pending_user_messages,
    process_worker_message,
    save_seen_message_ids,
)
from pregnancy_copilot.storage import PregnancyDataStore


def run_command(command: Sequence[str]) -> str:
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    return completed.stdout


def lark_command(args: list[str], profile: str | None = None) -> list[str]:
    if profile:
        return ["lark-cli", "--profile", profile, *args]
    return ["lark-cli", *args]


def list_messages(chat_id: str, profile: str | None, page_size: int) -> str:
    return run_command(
        lark_command(
            [
                "im",
                "+chat-messages-list",
                "--as",
                "bot",
                "--chat-id",
                chat_id,
                "--page-size",
                str(page_size),
                "--sort",
                "desc",
                "--format",
                "json",
            ],
            profile=profile,
        )
    )


def reply_to_message(message_id: str, reply_text: str, profile: str | None) -> None:
    run_command(
        lark_command(
            [
                "im",
                "+messages-reply",
                "--as",
                "bot",
                "--message-id",
                message_id,
                "--text",
                reply_text,
            ],
            profile=profile,
        )
    )


def run_once(
    chat_id: str,
    data_root: str | Path,
    state_file: str | Path,
    bot_app_id: str,
    profile: str | None,
    page_size: int,
    mark_existing: bool = False,
) -> int:
    seen = load_seen_message_ids(state_file)
    messages = parse_chat_messages_list(list_messages(chat_id, profile, page_size))
    if mark_existing:
        save_seen_message_ids(state_file, seen | {message.message_id for message in messages})
        return 0

    processed = 0
    store = PregnancyDataStore(data_root)
    for message in pending_user_messages(messages, seen, bot_app_id=bot_app_id):
        if store.event_exists(f"feishu-{message.message_id}"):
            seen.add(message.message_id)
            continue
        result = process_worker_message(message, data_root=data_root)
        if result.handled and result.reply_text:
            reply_to_message(message.message_id, result.reply_text, profile=profile)
        seen.add(message.message_id)
        processed += 1
    save_seen_message_ids(state_file, seen)
    return processed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chat-id", required=True)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--state-file", default="./pregnancy-data/runtime/feishu-seen-message-ids.json")
    parser.add_argument("--bot-app-id", default="")
    parser.add_argument("--profile", default=None, help="Optional lark-cli profile for this bot app.")
    parser.add_argument("--page-size", type=int, default=20)
    parser.add_argument("--interval", type=float, default=3.0)
    parser.add_argument("--max-loops", type=int, default=0, help="Stop after N polling loops; 0 means run forever.")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--mark-existing", action="store_true")
    parser.add_argument("--fail-fast", action="store_true", help="Exit on lark-cli/runtime errors instead of retrying.")
    args = parser.parse_args()

    loops = 0
    while True:
        try:
            processed = run_once(
                chat_id=args.chat_id,
                data_root=args.data_root,
                state_file=args.state_file,
                bot_app_id=args.bot_app_id,
                profile=args.profile,
                page_size=args.page_size,
                mark_existing=args.mark_existing,
            )
            print(f"processed={processed}", flush=True)
        except Exception as exc:
            print(f"worker_error={type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
            if args.fail_fast:
                raise
        if args.once or args.mark_existing:
            return
        loops += 1
        if args.max_loops and loops >= args.max_loops:
            return
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
