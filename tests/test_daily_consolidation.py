import yaml

from pregnancy_copilot.daily_consolidation import consolidate_day
from pregnancy_copilot.host_runtime import HostMessageRequest, process_host_message
from pregnancy_copilot.storage import PregnancyDataStore, SCHEMA_VERSION
from tests.helpers import make_profile_ready


def send(tmp_path, text: str, timestamp: str) -> None:
    process_host_message(
        HostMessageRequest(
            text=text,
            sender_id="pregnant-user",
            conversation_id="pregnancy-window",
            channel="host_agent",
            timestamp=timestamp,
        ),
        tmp_path,
    )


def test_consolidation_indexes_raw_messages_and_structured_events(tmp_path):
    make_profile_ready(tmp_path)
    send(tmp_path, "推荐一首歌", "2026-07-15T09:00:00+08:00")
    send(tmp_path, "今天有点焦虑，想聊聊", "2026-07-15T09:01:00+08:00")

    result = consolidate_day(
        PregnancyDataStore(tmp_path),
        "2026-07-15",
        ai_summary="今天主要聊了情绪和日常安排。",
    )
    index = yaml.safe_load(result.index_path.read_text(encoding="utf-8"))
    day = index["days"]["2026-07-15"]
    log = result.daily_log_path.read_text(encoding="utf-8")

    assert day["message_count"] == 2
    assert day["event_count"] == 1
    assert day["intents"] == {"mood_support": 1}
    assert day["raw_source_paths"] == ["inbox/raw_host_agent_messages/2026-07-15.md"]
    assert day["ai_summary"]["status"] == "ai_organized"
    assert day["ai_summary"]["medical_fact_effect"] == "none"
    assert "## 今日对话覆盖" in log
    assert "共 2 条本地原文记录" in log
    assert "[ai_organized]" in log
    assert "今天主要聊了情绪和日常安排" in log


def test_consolidation_is_idempotent_for_same_inputs(tmp_path):
    make_profile_ready(tmp_path)
    send(tmp_path, "今天体重 53kg", "2026-07-15T09:00:00+08:00")
    store = PregnancyDataStore(tmp_path)

    first = consolidate_day(store, "2026-07-15", ai_summary="记录了体重。")
    first_index = first.index_path.read_text(encoding="utf-8")
    first_log = first.daily_log_path.read_text(encoding="utf-8")
    second = consolidate_day(store, "2026-07-15", ai_summary="记录了体重。")

    assert second.index_path.read_text(encoding="utf-8") == first_index
    assert second.daily_log_path.read_text(encoding="utf-8") == first_log


def test_private_event_is_counted_without_expanding_private_text(tmp_path):
    make_profile_ready(tmp_path)
    store = PregnancyDataStore(tmp_path)
    store.append_event(
        {
            "schema_version": SCHEMA_VERSION,
            "event_id": "private-1",
            "timestamp": "2026-07-15T09:00:00+08:00",
            "intent": "mood_support",
            "privacy_level": "private",
            "user_message_summary": "不应出现在日志里的私密原文",
            "triage_required": False,
            "risk_level": "not_applicable",
        }
    )

    result = consolidate_day(store, "2026-07-15")
    index = yaml.safe_load(result.index_path.read_text(encoding="utf-8"))
    log = result.daily_log_path.read_text(encoding="utf-8")

    assert index["days"]["2026-07-15"]["private_event_count"] == 1
    assert "不应出现在日志里的私密原文" not in log
    assert "[private] private-1" in log


def test_missing_day_produces_truthful_empty_index(tmp_path):
    make_profile_ready(tmp_path)

    result = consolidate_day(PregnancyDataStore(tmp_path), "2026-07-14")
    index = yaml.safe_load(result.index_path.read_text(encoding="utf-8"))
    day = index["days"]["2026-07-14"]

    assert index["schema_version"] == "0.1"
    assert day["message_count"] == 0
    assert day["event_count"] == 0
    assert day["ai_summary"] is None


def test_consolidating_another_day_preserves_existing_index_entry(tmp_path):
    make_profile_ready(tmp_path)
    store = PregnancyDataStore(tmp_path)

    consolidate_day(store, "2026-07-14")
    result = consolidate_day(store, "2026-07-15")
    index = yaml.safe_load(result.index_path.read_text(encoding="utf-8"))

    assert list(index["days"]) == ["2026-07-14", "2026-07-15"]
