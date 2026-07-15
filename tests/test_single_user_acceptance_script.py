from scripts.run_single_user_acceptance import run_single_user_acceptance


def test_single_user_acceptance_covers_default_v01_path(tmp_path):
    result = run_single_user_acceptance(tmp_path)

    assert result["ok"] is True
    assert result["checks"]["pregnant_user_default"] is True
    assert result["checks"]["partner_share_disabled_by_default"] is True
    assert result["checks"]["general_chat_uses_minimal_context"] is True
    assert result["checks"]["pregnancy_symptom_has_context_package"] is True
    assert result["checks"]["medical_state_uses_latest_value"] is True
    assert result["medical_state"]["current_value"] == "31mm"
    assert result["medical_state"]["previous_values"][0]["effective_status"] == "superseded"
