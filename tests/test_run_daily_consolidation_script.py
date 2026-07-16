from scripts.run_daily_consolidation import run_daily_consolidation
from tests.helpers import make_profile_ready


def test_daily_consolidation_script_returns_scheduler_friendly_result(tmp_path):
    make_profile_ready(tmp_path)

    result = run_daily_consolidation(tmp_path, "2026-07-15", ai_summary=None)

    assert result["ok"] is True
    assert result["date"] == "2026-07-15"
    assert result["message_count"] == 0
    assert result["event_count"] == 0
    assert result["daily_log_path"].endswith("daily_logs/2026-07-15.md")
    assert result["index_path"].endswith("memory/daily_conversation_index.yaml")
