from scripts.run_host_channel_acceptance import run_host_channel_acceptance


def test_host_channel_acceptance_uses_agent_default_as_pregnant_user_channel(tmp_path):
    result = run_host_channel_acceptance(tmp_path)

    assert result["ok"] is True
    assert result["checks"]["host_channel_symptom_handled"] is True
    assert result["checks"]["host_channel_general_chat_passes_through"] is True
    assert result["checks"]["raw_agent_default_inbox_written"] is True
    assert result["symptom"]["host_request"]["channel"] == "agent_default"
    assert result["symptom"]["host_action"]["type"] == "answer_with_context_package"
    assert result["general_chat"]["host_action"]["type"] == "pass_through"
