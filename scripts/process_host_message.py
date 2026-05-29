from __future__ import annotations

import argparse
import json
from pathlib import Path

from pregnancy_copilot.host_runtime import HostMessageRequest, process_host_message


def run_host_message(
    data_root: str | Path,
    text: str,
    sender_id: str,
    sender_role: str = "pregnant_user",
    conversation_id: str = "host-conversation",
    channel: str = "host_agent",
    chat_type: str = "p2p",
    timestamp: str | None = None,
) -> dict:
    result = process_host_message(
        HostMessageRequest(
            text=text,
            sender_id=sender_id,
            sender_role=sender_role,
            conversation_id=conversation_id,
            channel=channel,
            chat_type=chat_type,
            timestamp=timestamp,
        ),
        data_root=data_root,
    )
    return {
        "ok": True,
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--text", required=True)
    parser.add_argument("--sender-id", required=True)
    parser.add_argument("--sender-role", default="pregnant_user")
    parser.add_argument("--conversation-id", default="host-conversation")
    parser.add_argument("--channel", default="host_agent")
    parser.add_argument("--chat-type", default="p2p")
    parser.add_argument("--timestamp")
    args = parser.parse_args()

    result = run_host_message(
        data_root=args.data_root,
        text=args.text,
        sender_id=args.sender_id,
        sender_role=args.sender_role,
        conversation_id=args.conversation_id,
        channel=args.channel,
        chat_type=args.chat_type,
        timestamp=args.timestamp,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
