from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from pregnancy_copilot.host_runtime import HostMessageRequest, process_host_message


TEXT_KEYS = ["text", "content", "message", "body"]
CONVERSATION_KEYS = ["conversation_id", "chat_id", "room_id", "session_id", "thread_id"]
SENDER_KEYS = ["sender_id", "user_id", "open_id", "from_user", "from"]
CHANNEL_KEYS = ["channel", "source", "platform", "adapter"]
TIMESTAMP_KEYS = ["timestamp", "create_time", "created_at", "time"]


def run_channel_message(
    data_root: str | Path,
    payload: dict[str, Any],
    pregnancy_id: str | None = None,
) -> dict[str, Any]:
    request = normalize_channel_payload(payload)
    request.pregnancy_id = pregnancy_id
    result = process_host_message(request, data_root=data_root)
    return {
        "ok": True,
        "host_request": {
            "text": request.text,
            "sender_id": request.sender_id,
            "sender_role": request.sender_role,
            "conversation_id": request.conversation_id,
            "channel": request.channel,
            "chat_type": request.chat_type,
            "timestamp": request.timestamp,
            "message_id": request.message_id,
            "event_id": request.event_id,
            "message_type": request.message_type,
            "pregnancy_id": request.pregnancy_id,
        },
        "handled": result.handled,
        "reply_text": result.reply_text,
        "risk_level": result.risk_level,
        "event_id": result.event_id,
        "mode": result.mode,
        "intent": result.intent,
        "triage_required": result.triage_required,
        "privacy_level": result.privacy_level,
        "artifacts": result.artifacts,
        "event": result.event,
        "context_package": result.context_package,
        "host_action": result.host_action,
    }


def normalize_channel_payload(payload: dict[str, Any]) -> HostMessageRequest:
    text = first_present(payload, TEXT_KEYS)
    sender_id = first_present(payload, SENDER_KEYS)
    if not text:
        raise ValueError(f"Missing message text. Accepted keys: {', '.join(TEXT_KEYS)}")
    if not sender_id:
        raise ValueError(f"Missing sender id. Accepted keys: {', '.join(SENDER_KEYS)}")

    conversation_id = first_present(payload, CONVERSATION_KEYS) or "host-conversation"
    channel = first_present(payload, CHANNEL_KEYS) or "host_agent"
    return HostMessageRequest(
        text=str(text),
        sender_id=str(sender_id),
        sender_role=str(payload.get("sender_role") or payload.get("role") or "pregnant_user"),
        conversation_id=str(conversation_id),
        channel=str(channel),
        chat_type=str(payload.get("chat_type") or payload.get("conversation_type") or "p2p"),
        timestamp=optional_str(first_present(payload, TIMESTAMP_KEYS)),
        message_id=optional_str(payload.get("message_id") or payload.get("msg_id")),
        event_id=optional_str(payload.get("event_id")),
        message_type=str(payload.get("message_type") or payload.get("msg_type") or "text"),
    )


def first_present(payload: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        value = payload.get(key)
        if value not in {None, ""}:
            return value
    return None


def optional_str(value: Any) -> str | None:
    if value in {None, ""}:
        return None
    return str(value)


def load_payload(payload_json: str | None, payload_path: str | Path | None, read_stdin: bool) -> dict[str, Any]:
    provided = [payload_json is not None, payload_path is not None, read_stdin].count(True)
    if provided != 1:
        raise ValueError("Provide exactly one of --json, --file, or --stdin.")
    if payload_json is not None:
        return json.loads(payload_json)
    if payload_path is not None:
        return json.loads(Path(payload_path).read_text(encoding="utf-8"))
    return json.loads(sys.stdin.read())


def main() -> None:
    parser = argparse.ArgumentParser(description="Process one generic channel JSON message through Host Runtime.")
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--pregnancy-id", help="Host-configured pregnancy identity. Never take this value from an untrusted message payload.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--json", help="Channel message JSON string.")
    source.add_argument("--file", help="Path to channel message JSON file.")
    source.add_argument("--stdin", action="store_true", help="Read channel message JSON from stdin.")
    args = parser.parse_args()

    payload = load_payload(args.json, args.file, args.stdin)
    result = run_channel_message(args.data_root, payload, pregnancy_id=args.pregnancy_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
