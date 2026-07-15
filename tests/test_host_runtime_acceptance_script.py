from scripts.run_host_runtime_acceptance import run_host_runtime_acceptance


def test_host_runtime_acceptance_covers_host_contract(tmp_path):
    result = run_host_runtime_acceptance(tmp_path)

    assert result["ok"] is True
    assert result["checks"]["general_chat_uses_minimal_context"] is True
    assert result["checks"]["symptom_handled_with_context_package"] is True
    assert result["checks"]["daily_log_without_visible_triage"] is True
    assert result["checks"]["latest_medical_state_wins"] is True
    assert result["checks"]["old_medical_state_superseded"] is True
    assert result["checks"]["report_question_context_uses_current_state"] is True
    assert result["checks"]["general_chat_host_action_uses_context"] is True
    assert result["checks"]["fresh_profile_triggers_onboarding"] is True
    assert result["host_contract"]["general_chat"]["handled"] is True
    assert result["host_contract"]["general_chat"]["host_action_type"] == "answer_with_context_package"
    assert result["host_contract"]["daily_log"]["risk_level"] == "not_applicable"
    assert result["host_contract"]["report_question"]["current_cervical_length"] == "31mm"
