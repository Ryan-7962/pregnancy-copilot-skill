from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from pregnancy_copilot.feishu_smoke import (
    build_list_messages_command,
    build_send_message_command,
    parse_message_list_output,
    parse_send_message_output,
    summarize_smoke_outputs,
)

try:
    from scripts.init_data_dir import initialize_data_dir
except ModuleNotFoundError:
    from init_data_dir import initialize_data_dir


DEFAULT_MESSAGE = "Pregnancy Copilot P2P smoke test：今天肚子有点紧，休息后好了，没有流血也没有流水。无隐私内容。"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a real Feishu P2P smoke test against the bot.")
    parser.add_argument("--data-root", default="/tmp/pregnancy-copilot-feishu-p2p-smoke")
    parser.add_argument("--bot-open-id", required=True, help="Bot open_id, e.g. ou_xxx.")
    parser.add_argument("--message", default=DEFAULT_MESSAGE)
    parser.add_argument("--timeout", default="45s")
    parser.add_argument("--profile", default=None, help="Optional lark-cli profile name, e.g. <lark-profile>.")
    args = parser.parse_args()

    root = Path(args.data_root)
    initialize_data_dir(root)
    listener = subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).resolve().parent / "run_feishu_event_loop.py"),
            "--data-root",
            str(root),
            "--max-events",
            "1",
            "--timeout",
            args.timeout,
            *(["--profile", args.profile] if args.profile else []),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parent.parent / "src")},
    )
    time.sleep(1)

    send_process = subprocess.run(
        build_send_message_command(args.bot_open_id, args.message, profile=args.profile),
        capture_output=True,
        text=True,
    )
    if send_process.returncode != 0:
        terminate(listener)
        raise SystemExit(send_process.stderr or send_process.stdout)
    send_result = parse_send_message_output(send_process.stdout)
    try:
        listener.wait(timeout=parse_timeout_seconds(args.timeout) + 10)
    except subprocess.TimeoutExpired:
        terminate(listener)

    list_process = subprocess.run(
        build_list_messages_command(send_result["chat_id"], profile=args.profile),
        capture_output=True,
        text=True,
        check=False,
    )
    recent_messages = parse_message_list_output(list_process.stdout) if list_process.returncode == 0 else []
    report = summarize_smoke_outputs(
        data_root=root,
        marker=args.message,
        send_result=send_result,
        recent_messages=recent_messages,
    )
    report["listener_returncode"] = listener.returncode
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["ok"]:
        raise SystemExit(1)


def parse_timeout_seconds(value: str) -> int:
    text = value.strip().lower()
    if text.endswith("s"):
        return int(text[:-1])
    return int(text)


def terminate(process: subprocess.Popen) -> None:
    if process.poll() is None:
        process.terminate()
        process.wait(timeout=5)


if __name__ == "__main__":
    main()
