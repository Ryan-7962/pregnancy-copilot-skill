from scripts.init_data_dir import initialize_data_dir
from scripts.rebuild_memory import rebuild_memory
from pregnancy_copilot.storage import PregnancyDataStore


def test_rebuild_memory_regenerates_context_timeline_pattern_and_daily_log(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    store.append_event(
        {
            "schema_version": "0.1",
            "event_id": "event-001",
            "event_type": "prenatal_report",
            "timestamp": "2026-05-05T09:00:00+08:00",
            "gestational_age": "8w2d",
            "raw_source_path": "reports/demo.md",
            "user_message_summary": "B 超报告问题，今天有点焦虑",
            "assistant_response_summary": "先接住情绪，再整理问题问医生。",
            "risk_level": "yellow",
        }
    )

    result = rebuild_memory(tmp_path, date="2026-05-05")

    assert result["current_context"].endswith("memory/current_context.md")
    assert result["medical_timeline"].endswith("memory/medical_timeline.md")
    assert result["emotional_pattern"].endswith("memory/emotional_pattern.md")
    assert result["daily_log"].endswith("daily_logs/2026-05-05.md")
    assert "B 超报告问题" in (tmp_path / "memory" / "medical_timeline.md").read_text(encoding="utf-8")
    assert "焦虑" in (tmp_path / "memory" / "emotional_pattern.md").read_text(encoding="utf-8")
