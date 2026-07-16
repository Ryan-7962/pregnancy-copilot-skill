from __future__ import annotations

from pathlib import Path
from contextlib import contextmanager
import fcntl
import json
import os
import re
import tempfile
from datetime import datetime
from typing import Any
import unicodedata

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
            "external_sources/raw",
            "external_sources/media",
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

        event_source = safe_path_component(str(event_source), "source")
        date = safe_iso_date(timestamp)
        path = self.root / "inbox" / f"raw_{event_source}_messages" / f"{date}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        block = ["\n\n---\n"]
        block.extend(f"{key}: {single_line_metadata(value)}\n" for key, value in metadata.items())
        block.extend(["---\n\n", f"{text}\n"])
        with self.transaction_lock(f"raw-{event_source}-{date}"):
            message_id = str(metadata.get("message_id") or "")
            if message_id and raw_message_exists(path, message_id):
                return path
            append_text_durable(path, "".join(block))
        return path

    def append_event(self, event: dict, filename: str = "events.jsonl", dedupe_by_event_id: bool = False) -> Path:
        self.validate_schema_version(event)
        self.ensure_dirs()
        filename = safe_path_component(filename, "filename")
        path = self.root / "events" / filename
        with self.transaction_lock(f"events-{filename}"):
            if dedupe_by_event_id and self.event_exists(str(event.get("event_id", "")), filename=filename):
                return path
            append_text_durable(path, json.dumps(event, ensure_ascii=False) + "\n")
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

    @contextmanager
    def transaction_lock(self, name: str):
        safe_name = safe_path_component(name, "lock name")
        lock_dir = self.root / ".locks"
        lock_dir.mkdir(parents=True, exist_ok=True)
        lock_path = lock_dir / f"{safe_name}.lock"
        with lock_path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

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


def safe_path_component(value: str, field: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip()
    if (
        not normalized
        or normalized in {".", ".."}
        or ".." in normalized
        or "/" in normalized
        or "\\" in normalized
        or "\x00" in normalized
        or any(ord(char) < 32 for char in normalized)
    ):
        raise ValueError(f"Unsafe {field}: {value!r}")
    return re.sub(r"[^\w.-]", "_", normalized, flags=re.UNICODE)


def safe_iso_date(timestamp: str) -> str:
    value = str(timestamp)[:10]
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(f"Unsafe timestamp: {timestamp!r}") from exc
    return value


def append_text_durable(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())


def raw_message_exists(path: Path, message_id: str) -> bool:
    if not path.exists():
        return False
    marker = f"message_id: {single_line_metadata(message_id)}\n"
    return marker in path.read_text(encoding="utf-8")


def single_line_metadata(value: Any) -> str:
    return str(value).replace("\r", "\\r").replace("\n", "\\n")


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()
