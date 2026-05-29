from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .host_runtime import HostMessageRequest, HostMessageResult, process_host_message


@dataclass(frozen=True)
class FeishuWorkerMessage:
    message_id: str
    chat_id: str
    sender_id: str
    sender_type: str
    sender_app_id: str
    text: str
    create_time: str
    message_position: int
    msg_type: str


def load_seen_message_ids(path: str | Path) -> set[str]:
    path = Path(path)
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return {str(item) for item in data}
    if isinstance(data, dict):
        return {str(item) for item in data.get("message_ids", [])}
    return set()


def save_seen_message_ids(path: str | Path, message_ids: Iterable[str]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"message_ids": sorted({str(item) for item in message_ids if item})}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_chat_messages_list(output: str) -> list[FeishuWorkerMessage]:
    data = json.loads(output)
    messages = data.get("data", {}).get("messages", []) if isinstance(data, dict) else []
    parsed = [parse_lark_message(item) for item in messages]
    return [message for message in parsed if message is not None]


def parse_lark_message(item: dict) -> FeishuWorkerMessage | None:
    message_id = str(item.get("message_id") or "")
    chat_id = str(item.get("chat_id") or "")
    sender = item.get("sender") or {}
    sender_id = str(sender.get("id") or "")
    content = item.get("content")
    text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
    if not message_id or not chat_id:
        return None
    return FeishuWorkerMessage(
        message_id=message_id,
        chat_id=chat_id,
        sender_id=sender_id,
        sender_type=str(sender.get("sender_type") or ""),
        sender_app_id=sender_id if sender.get("id_type") == "app_id" else "",
        text=text.strip(),
        create_time=str(item.get("create_time") or ""),
        message_position=parse_position(item.get("message_position")),
        msg_type=str(item.get("msg_type") or ""),
    )


def parse_position(value: object) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0


def pending_user_messages(
    messages: Iterable[FeishuWorkerMessage],
    seen_message_ids: set[str],
    bot_app_id: str,
) -> list[FeishuWorkerMessage]:
    pending = []
    for message in messages:
        if message.message_id in seen_message_ids:
            continue
        if message.sender_type != "user":
            continue
        if bot_app_id and message.sender_app_id == bot_app_id:
            continue
        if not message.text:
            continue
        pending.append(message)
    return sorted(pending, key=lambda item: item.message_position)


def process_worker_message(message: FeishuWorkerMessage, data_root: str | Path) -> HostMessageResult:
    return process_host_message(
        HostMessageRequest(
            text=message.text,
            sender_id=message.sender_id,
            sender_role="pregnant_user",
            conversation_id=message.chat_id,
            channel="feishu",
            chat_type="p2p",
            timestamp=message.create_time,
            message_id=message.message_id,
            event_id=f"feishu-{message.message_id}",
            message_type=message.msg_type or "text",
        ),
        data_root=data_root,
    )
