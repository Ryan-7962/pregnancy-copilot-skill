from __future__ import annotations

from pathlib import Path
import json
from datetime import datetime
from typing import Any

import yaml

from .models import MessageEvent


SCHEMA_VERSION = "0.1"


class SchemaVersionError(ValueError):
    pass

class PregnancyDataStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)

    def ensure_dirs(self) -> None:
        for rel in [
            "inbox/raw_feishu_messages",
            "inbox/raw_dad_diary",
            "events",
            "memory",
            "reports",
            "daily_logs",
            "weekly_reviews",
            "husband_summaries",
            "baby_diaries",
            "doctor_questions",
            "backups",
        ]:
            (self.root / rel).mkdir(parents=True, exist_ok=True)

    def save_raw_message(self, message: MessageEvent | str, source: str = "feishu") -> Path:
        self.ensure_dirs()
        if isinstance(message, MessageEvent):
            event_source = message.source
            timestamp = message.timestamp
            text = message.text
            metadata = {
                "message_id": message.message_id,
                "timestamp": timestamp,
                "sender_id": message.sender_id,
                "sender_role": message.sender_role,
                "chat_type": message.chat_type,
                "source": event_source,
            }
            if message.chat_id:
                metadata["chat_id"] = message.chat_id
            if message.event_id:
                metadata["event_id"] = message.event_id
            if message.message_type:
                metadata["message_type"] = message.message_type
        else:
            event_source = source
            timestamp = datetime.now().astimezone().isoformat()
            text = message
            metadata = {
                "timestamp": timestamp,
                "source": event_source,
            }

        date = timestamp[:10]
        path = self.root / "inbox" / f"raw_{event_source}_messages" / f"{date}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write("\n\n---\n")
            for key, value in metadata.items():
                f.write(f"{key}: {value}\n")
            f.write("---\n\n")
            f.write(f"{text}\n")
        return path

    def append_event(self, event: dict, filename: str = "events.jsonl", dedupe_by_event_id: bool = False) -> Path:
        self.validate_schema_version(event)
        self.ensure_dirs()
        path = self.root / "events" / filename
        if dedupe_by_event_id and self.event_exists(str(event.get("event_id", "")), filename=filename):
            return path
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
        return path

    def event_exists(self, event_id: str, filename: str = "events.jsonl") -> bool:
        if not event_id:
            return False
        path = self.root / "events" / filename
        if not path.exists():
            return False
        with path.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if str(row.get("event_id") or "") == event_id:
                    return True
        return False

    def load_profile(self) -> dict[str, Any]:
        path = self.root / "memory" / "profile.yaml"
        if not path.exists():
            raise FileNotFoundError(path)
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        self.validate_schema_version(data)
        return data

    def validate_schema_version(self, payload: dict[str, Any]) -> None:
        version = payload.get("schema_version")
        if version != SCHEMA_VERSION:
            raise SchemaVersionError(f"Unsupported schema_version: {version!r}; expected {SCHEMA_VERSION!r}")
