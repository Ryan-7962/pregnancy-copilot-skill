from scripts.init_data_dir import initialize_data_dir
from scripts.check_profile_readiness import run_profile_readiness_check
from tests.helpers import make_profile_ready


def test_profile_readiness_flags_template_defaults(tmp_path):
    initialize_data_dir(tmp_path)

    result = run_profile_readiness_check(tmp_path)

    assert result["ok"] is False
    assert result["status"] == "needs_review"
    assert "current_gestational_age" in result["missing_or_template_fields"]
    assert "hospital.name" in result["optional_missing_fields"]
    assert "current_gestational_age" in result["missing_or_template_fields"]
    assert "profile_name" in result["optional_missing_fields"]
    assert result["checks"]["privacy_defaults"]["ok"] is True


def test_profile_readiness_passes_when_required_fields_are_real(tmp_path):
    make_profile_ready(tmp_path)

    result = run_profile_readiness_check(tmp_path)

    assert result["ok"] is True
    assert result["status"] == "ready"
    assert result["missing_or_template_fields"] == []
    assert result["checks"]["pregnancy_anchor"]["ok"] is True
    assert result["checks"]["hospital"]["ok"] is True
