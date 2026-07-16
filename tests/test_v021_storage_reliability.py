import json
from concurrent.futures import ThreadPoolExecutor

import pytest

import pregnancy_copilot
from pregnancy_copilot import context_builder, daily_metrics
from pregnancy_copilot.context_builder import build_current_context
from pregnancy_copilot.daily_metrics import build_daily_metrics_index
from pregnancy_copilot.data_init import initialize_data_dir
from pregnancy_copilot.host_runtime import HostMessageRequest, process_host_message
from pregnancy_copilot.models import MessageEvent
from pregnancy_copilot import storage
from pregnancy_copilot.storage import PregnancyDataStore, SCHEMA_VERSION
from tests.helpers import make_profile_ready


def test_untrusted_channel_cannot_escape_data_root(tmp_path):
    store = PregnancyDataStore(tmp_path)
    message = MessageEvent(
        message_id="msg-escape",
        timestamp="2026-07-15T10:00:00+08:00",
        sender_id="user",
        sender_role="pregnant_user",
        chat_type="p2p",
        text="test",
        source="../../../../../escaped",
    )

    with pytest.raises(ValueError, match="Unsafe source"):
        store.save_raw_message(message)
    assert not list(tmp_path.parent.glob("escaped*"))


def test_distinct_message_ids_in_same_second_are_both_persisted(tmp_path):
    make_profile_ready(tmp_path)
    base = {
        "sender_id": "pregnant-user",
        "conversation_id": "pregnancy-window",
        "channel": "agent_default",
        "timestamp": "2026-07-15T10:00:00+08:00",
    }

    first = process_host_message(
        HostMessageRequest(text="今天体重 50kg", message_id="msg-weight-1", **base),
        data_root=tmp_path,
    )
    second = process_host_message(
        HostMessageRequest(text="今天体重 51kg", message_id="msg-weight-2", **base),
        data_root=tmp_path,
    )

    rows = [json.loads(line) for line in (tmp_path / "events" / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    assert first.event_id == "msg-weight-1"
    assert second.event_id == "msg-weight-2"
    assert [row["event_id"] for row in rows] == ["msg-weight-1", "msg-weight-2"]


def test_true_duplicate_message_id_remains_idempotent(tmp_path):
    make_profile_ready(tmp_path)
    request = HostMessageRequest(
        text="今天体重 50kg",
        sender_id="pregnant-user",
        conversation_id="pregnancy-window",
        channel="agent_default",
        timestamp="2026-07-15T10:00:00+08:00",
        message_id="msg-same",
    )

    process_host_message(request, data_root=tmp_path)
    process_host_message(request, data_root=tmp_path)

    rows = (tmp_path / "events" / "events.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(rows) == 1
    raw = (tmp_path / "inbox" / "raw_agent_default_messages" / "2026-07-15.md").read_text(encoding="utf-8")
    assert raw.count("message_id: msg-same") == 1


def test_concurrent_event_appends_are_complete_and_valid_jsonl(tmp_path):
    store = PregnancyDataStore(tmp_path)

    def append(index: int) -> None:
        store.append_event(
            {
                "schema_version": SCHEMA_VERSION,
                "event_id": f"evt-{index:03d}",
                "event_type": "test",
                "timestamp": "2026-07-15T10:00:00+08:00",
            },
            dedupe_by_event_id=True,
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(append, range(100)))

    rows = [json.loads(line) for line in (tmp_path / "events" / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 100
    assert len({row["event_id"] for row in rows}) == 100


def test_concurrent_duplicate_delivery_is_written_once(tmp_path):
    store = PregnancyDataStore(tmp_path)
    event = {
        "schema_version": SCHEMA_VERSION,
        "event_id": "evt-shared",
        "event_type": "test",
        "timestamp": "2026-07-15T10:00:00+08:00",
    }

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(lambda _: store.append_event(event, dedupe_by_event_id=True), range(100)))

    rows = (tmp_path / "events" / "events.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(rows) == 1


def test_runtime_version_matches_release_version():
    assert pregnancy_copilot.__version__ == "0.4.0"


def test_current_context_uses_atomic_write(tmp_path, monkeypatch):
    initialize_data_dir(tmp_path)
    calls = []

    def capture(path, text):
        calls.append(path)
        storage.atomic_write_text(path, text)

    monkeypatch.setattr(context_builder, "atomic_write_text", capture)

    output = build_current_context(PregnancyDataStore(tmp_path))

    assert calls == [output]


def test_daily_metrics_outputs_use_atomic_write(tmp_path, monkeypatch):
    initialize_data_dir(tmp_path)
    calls = []

    def capture(path, text):
        calls.append(path)
        storage.atomic_write_text(path, text)

    monkeypatch.setattr(daily_metrics, "atomic_write_text", capture)

    build_daily_metrics_index(PregnancyDataStore(tmp_path))

    assert calls == [
        tmp_path / "memory" / "daily_metrics.yaml",
        tmp_path / "memory" / "daily_metrics.md",
    ]
