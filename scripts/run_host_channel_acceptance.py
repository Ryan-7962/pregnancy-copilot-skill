from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
import yaml

from pregnancy_copilot.data_init import initialize_data_dir

try:
    from scripts.process_channel_message import run_channel_message
except ModuleNotFoundError:
    from process_channel_message import run_channel_message


def run_host_channel_acceptance(
    data_root: str | Path,
    channel: str = "agent_default",
    conversation_id: str = "pregnancy-default-chat",
    sender_id: str = "pregnant-user",
) -> dict[str, Any]:
    data_root = Path(data_root)
    make_profile_ready(data_root)
    symptom = run_channel_message(
        data_root,
        {
            "channel": channel,
            "chat_id": conversation_id,
            "sender_id": sender_id,
            "text": "今天肚子有点紧，休息后好了，没有流血也没有流水",
            "timestamp": "2026-05-16T20:00:00+08:00",
        },
    )
    general_chat = run_channel_message(
        data_root,
        {
            "channel": channel,
            "chat_id": conversation_id,
            "sender_id": sender_id,
            "text": "推荐一首歌",
            "timestamp": "2026-05-16T20:01:00+08:00",
        },
    )
    inbox_path = data_root / "inbox" / f"raw_{channel}_messages" / "2026-05-16.md"
    checks = {
        "host_channel_symptom_handled": symptom["handled"] is True
        and symptom["host_action"]["type"] == "answer_with_context_package"
        and symptom["context_package"]["channel"] == channel,
        "host_channel_general_chat_uses_context": general_chat["handled"] is True
        and general_chat["intent"] == "pregnancy_context"
        and general_chat["host_action"]["type"] == "answer_with_context_package",
        "raw_agent_default_inbox_written": inbox_path.exists(),
    }
    return {
        "ok": all(checks.values()),
        "checks": checks,
        "topology": {
            "meaning": "Treat the host Agent default chat as the pregnant user's conversation channel.",
            "channel": channel,
            "conversation_id": conversation_id,
            "sender_id": sender_id,
        },
        "symptom": {
            "handled": symptom["handled"],
            "intent": symptom["intent"],
            "risk_level": symptom["risk_level"],
            "host_request": symptom["host_request"],
            "host_action": symptom["host_action"],
            "raw_source_path": symptom["artifacts"].get("raw_source_path"),
        },
        "general_chat": {
            "handled": general_chat["handled"],
            "intent": general_chat["intent"],
            "host_action": general_chat["host_action"],
        },
        "paths": {
            "data_root": str(data_root),
            "raw_inbox": str(inbox_path),
        },
    }


def make_profile_ready(data_root: str | Path) -> None:
    root = initialize_data_dir(data_root)
    profile_path = root / "memory" / "profile.yaml"
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    profile.update(
        profile_name="Acceptance Pregnancy Profile",
        display_name="验收用户",
        baby_nickname="验收宝宝",
        current_gestational_age="23w1d",
    )
    profile_path.write_text(yaml.safe_dump(profile, allow_unicode=True, sort_keys=False), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run host Agent default channel pregnant-user channel acceptance checks.")
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--channel", default="agent_default")
    parser.add_argument("--conversation-id", default="pregnancy-default-chat")
    parser.add_argument("--sender-id", default="pregnant-user")
    args = parser.parse_args()

    result = run_host_channel_acceptance(
        data_root=args.data_root,
        channel=args.channel,
        conversation_id=args.conversation_id,
        sender_id=args.sender_id,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
