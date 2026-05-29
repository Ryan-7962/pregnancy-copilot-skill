from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_send_message_command(bot_open_id: str, message: str, profile: str | None = None) -> list[str]:
    return lark_command(
        [
        "im",
        "+messages-send",
        "--as",
        "user",
        "--user-id",
        bot_open_id,
        "--text",
        message,
        ],
        profile=profile,
    )


def build_list_messages_command(chat_id: str, page_size: int = 10, profile: str | None = None) -> list[str]:
    return lark_command(
        [
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
        ],
        profile=profile,
    )


def lark_command(args: list[str], profile: str | None = None) -> list[str]:
    if profile:
        return ["lark-cli", "--profile", profile, *args]
    return ["lark-cli", *args]


def parse_send_message_output(stdout: str) -> dict[str, str]:
    payload = json.loads(stdout)
    data = payload.get("data") or {}
    return {"chat_id": data.get("chat_id", ""), "message_id": data.get("message_id", "")}


def parse_message_list_output(stdout: str) -> list[dict[str, Any]]:
    payload = json.loads(stdout)
    return list((payload.get("data") or {}).get("messages") or [])


def summarize_smoke_outputs(
    data_root: str | Path,
    marker: str,
    send_result: dict[str, str],
    recent_messages: list[dict[str, Any]],
) -> dict[str, Any]:
    root = Path(data_root)
    events_path = root / "events" / "events.jsonl"
    current_context_path = root / "memory" / "current_context.md"
    events = read_jsonl(events_path)
    matching_events = [
        event
        for event in events
        if marker in str(event.get("user_message_summary", "")) or marker in str(event.get("event_id", ""))
    ]
    latest_event = matching_events[-1] if matching_events else {}
    local_files = {
        "events_jsonl": events_path.exists(),
        "raw_message": any((root / "inbox" / "raw_feishu_messages").glob("*.md")),
        "daily_log": any((root / "daily_logs").glob("*.md")),
        "current_context": current_context_path.exists(),
    }
    bot_reply = find_bot_reply(recent_messages, send_result.get("message_id", ""))
    return {
        "ok": bool(matching_events) and all(local_files.values()) and bot_reply["ok"],
        "risk_level": latest_event.get("risk_level"),
        "event_id": latest_event.get("event_id"),
        "send_result": send_result,
        "local_files": local_files,
        "bot_reply": bot_reply,
    }


def find_bot_reply(messages: list[dict[str, Any]], reply_to_message_id: str) -> dict[str, Any]:
    for message in messages:
        sender = message.get("sender") or {}
        if message.get("reply_to") == reply_to_message_id and sender.get("sender_type") in {"app", "bot"}:
            return {"ok": True, "content": message.get("content", ""), "message_id": message.get("message_id", "")}
    return {"ok": False, "content": "", "message_id": ""}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records
