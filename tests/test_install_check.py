from scripts.install_check import run_install_check


def test_run_install_check_initializes_memory_and_generates_outputs(tmp_path):
    result = run_install_check(tmp_path / "check-data")

    assert result["ok"] is True
    assert result["raw_message"].endswith("inbox/raw_feishu_messages/2026-05-05.md")
    assert result["events"].endswith("events/events.jsonl")
    assert result["current_context"].endswith("memory/current_context.md")
    assert result["medical_timeline"].endswith("memory/medical_timeline.md")
    assert result["emotional_pattern"].endswith("memory/emotional_pattern.md")
    assert result["daily_log"].endswith("daily_logs/2026-05-05.md")
    assert result["onboarding_state"].endswith("memory/onboarding_state.yaml")
    assert result["prenatal_plan"].endswith("memory/prenatal_plan.yaml")
    assert result["daily_index"].endswith("memory/daily_conversation_index.yaml")
    assert result["risk_level"] == "green"
    assert result["onboarding_action"]["type"] == "collect_profile"
    assert result["onboarding_action"]["send_reply"] is True
    assert "我是你的孕期助手" in result["onboarding_action"]["reply_text"]
    assert result["onboarding_action"]["blocking"] is False
