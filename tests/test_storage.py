import json
from pathlib import Path

import pytest

from scripts.init_data_dir import initialize_data_dir
from pregnancy_copilot.models import MessageEvent
from pregnancy_copilot.storage import PregnancyDataStore, SchemaVersionError


def test_initialize_data_dir_creates_full_structure_and_profile(tmp_path):
    initialize_data_dir(tmp_path)

    expected_dirs = [
        "inbox/raw_feishu_messages",
        "inbox/raw_gemini_exports",
        "inbox/raw_notebooklm_exports",
        "inbox/raw_obsidian_notes",
        "inbox/raw_dad_diary",
        "events",
        "memory",
        "reports",
        "daily_logs",
        "weekly_reviews",
        "husband_summaries",
        "baby_diaries",
        "doctor_questions",
        "feishu_docs",
        "exports",
        "backups",
    ]
    for rel in expected_dirs:
        assert (tmp_path / rel).is_dir()

    profile_path = tmp_path / "memory" / "profile.yaml"
    assert profile_path.exists()
    profile = PregnancyDataStore(tmp_path).load_profile()
    assert profile["schema_version"] == "0.1"
    assert profile["baby_nickname"] == "宝宝"
    assert profile["privacy"]["default_privacy_level"] == "summary"
    assert profile["preferences"]["partner_share_default"] == "private"
    assert profile["preferences"]["husband_share_default"] == "private"


def test_save_raw_message_writes_inbox_with_traceable_metadata(tmp_path):
    store = PregnancyDataStore(tmp_path)
    message = MessageEvent(
        message_id="m-001",
        timestamp="2026-05-05T08:30:00+08:00",
        sender_id="u-001",
        sender_role="pregnant_user",
        chat_type="private",
        text="今天肚子有点紧，休息后好了",
    )

    path = store.save_raw_message(message)

    assert path == tmp_path / "inbox" / "raw_feishu_messages" / "2026-05-05.md"
    content = path.read_text(encoding="utf-8")
    assert "message_id: m-001" in content
    assert "sender_role: pregnant_user" in content
    assert "今天肚子有点紧，休息后好了" in content


def test_append_event_is_append_only_jsonl_and_requires_schema_version(tmp_path):
    store = PregnancyDataStore(tmp_path)
    event = {
        "schema_version": "0.1",
        "event_id": "event-001",
        "event_type": "symptom_qa",
        "timestamp": "2026-05-05T08:30:00+08:00",
    }

    path = store.append_event(event)
    store.append_event({**event, "event_id": "event-002"})

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert [row["event_id"] for row in rows] == ["event-001", "event-002"]

    with pytest.raises(SchemaVersionError):
        store.append_event({"event_id": "missing-schema"})


def test_append_event_can_dedupe_by_event_id(tmp_path):
    store = PregnancyDataStore(tmp_path)
    event = {
        "schema_version": "0.1",
        "event_id": "event-001",
        "event_type": "symptom_qa",
        "timestamp": "2026-05-05T08:30:00+08:00",
    }

    path = store.append_event(event, dedupe_by_event_id=True)
    store.append_event({**event, "event_type": "pregnancy_log"}, dedupe_by_event_id=True)
    store.append_event({**event, "event_id": "event-002"}, dedupe_by_event_id=True)

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert [row["event_id"] for row in rows] == ["event-001", "event-002"]
    assert store.event_exists("event-001")
    assert not store.event_exists("event-missing")


def test_load_profile_rejects_unknown_schema_version(tmp_path):
    initialize_data_dir(tmp_path)
    profile_path = tmp_path / "memory" / "profile.yaml"
    profile_path.write_text('schema_version: "9.9"\n', encoding="utf-8")

    with pytest.raises(SchemaVersionError):
        PregnancyDataStore(tmp_path).load_profile()
