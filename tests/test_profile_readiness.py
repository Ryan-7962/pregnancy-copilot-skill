from scripts.init_data_dir import initialize_data_dir
from scripts.check_profile_readiness import run_profile_readiness_check


def test_profile_readiness_flags_template_defaults(tmp_path):
    initialize_data_dir(tmp_path)

    result = run_profile_readiness_check(tmp_path)

    assert result["ok"] is False
    assert result["status"] == "needs_review"
    assert "hospital.name" in result["missing_or_template_fields"]
    assert "current_gestational_age" in result["missing_or_template_fields"]
    assert "profile_name" in result["missing_or_template_fields"]
    assert result["checks"]["privacy_defaults"]["ok"] is True


def test_profile_readiness_passes_when_required_fields_are_real(tmp_path):
    initialize_data_dir(tmp_path)
    profile_path = tmp_path / "memory" / "profile.yaml"
    profile_text = profile_path.read_text(encoding="utf-8")
    profile_text = profile_text.replace('profile_name: "Example Pregnancy Profile"', 'profile_name: "Custom Pregnancy Profile"')
    profile_text = profile_text.replace('display_name: "孕妇"', 'display_name: "孕妇用户"')
    profile_text = profile_text.replace('baby_nickname: "宝宝"', 'baby_nickname: "小宝宝"')
    profile_text = profile_text.replace('current_gestational_age: "20w0d"', 'current_gestational_age: "23w1d"')
    profile_text = profile_text.replace('name: "示例医院"', 'name: "示例市妇产医院"')
    profile_path.write_text(profile_text, encoding="utf-8")

    result = run_profile_readiness_check(tmp_path)

    assert result["ok"] is True
    assert result["status"] == "ready"
    assert result["missing_or_template_fields"] == []
    assert result["checks"]["pregnancy_anchor"]["ok"] is True
    assert result["checks"]["hospital"]["ok"] is True
