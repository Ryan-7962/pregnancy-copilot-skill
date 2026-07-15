import zipfile

import yaml

from pregnancy_copilot.data_init import initialize_data_dir
from pregnancy_copilot.migration_v021 import migrate_to_v021


def test_v021_migration_backs_up_then_clears_only_unedited_v020_template(tmp_path):
    initialize_data_dir(tmp_path)
    profile_path = tmp_path / "memory" / "profile.yaml"
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    profile.update(
        profile_name="Example Pregnancy Profile",
        display_name="孕妇",
        baby_nickname="宝宝",
        current_gestational_age="20w0d",
    )
    profile["hospital"] = {
        "name": "示例医院",
        "city": "上海",
        "care_model": "中国大陆主要妇产科医院流程",
    }
    profile["current_focus"] = ["20 周大排畸", "胎盘位置", "宫颈长度", "睡眠和焦虑"]
    profile_path.write_text(yaml.safe_dump(profile, allow_unicode=True, sort_keys=False), encoding="utf-8")

    result = migrate_to_v021(tmp_path, date="2026-07-15")
    migrated = yaml.safe_load(profile_path.read_text(encoding="utf-8"))

    assert result["backup_verification"]["ok"] is True
    assert result["backup_verification"]["encrypted"] is False
    assert result["cleared_unedited_template"] is True
    assert migrated["profile_name"] is None
    assert migrated["current_gestational_age"] is None
    assert migrated["hospital"]["name"] is None
    assert migrated["current_focus"] == []
    with zipfile.ZipFile(result["backup_path"]) as archive:
        old_profile = yaml.safe_load(archive.read("memory/profile.yaml"))
    assert old_profile["current_gestational_age"] == "20w0d"
    assert "ZIP 默认未加密" in result["report_path"].read_text(encoding="utf-8")


def test_v021_migration_preserves_partially_customized_profile_and_requests_review(tmp_path):
    initialize_data_dir(tmp_path)
    profile_path = tmp_path / "memory" / "profile.yaml"
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    profile.update(display_name="真实用户", current_gestational_age="20w0d")
    profile_path.write_text(yaml.safe_dump(profile, allow_unicode=True, sort_keys=False), encoding="utf-8")

    result = migrate_to_v021(tmp_path, date="2026-07-15")
    migrated = yaml.safe_load(profile_path.read_text(encoding="utf-8"))

    assert result["cleared_unedited_template"] is False
    assert "current_gestational_age" in result["manual_review_fields"]
    assert migrated["display_name"] == "真实用户"
    assert migrated["current_gestational_age"] == "20w0d"
