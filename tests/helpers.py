from __future__ import annotations

from pathlib import Path

import yaml

from pregnancy_copilot.data_init import initialize_data_dir


def make_profile_ready(data_root: str | Path) -> None:
    root = initialize_data_dir(data_root)
    profile_path = root / "memory" / "profile.yaml"
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    profile.update(
        {
            "profile_name": "Test Pregnancy Profile",
            "display_name": "测试用户",
            "baby_nickname": "测试宝宝",
            "current_gestational_age": "23w1d",
        }
    )
    profile["hospital"] = {
        "name": "测试医院",
        "city": "上海",
        "care_model": "测试产检流程",
    }
    profile_path.write_text(yaml.safe_dump(profile, allow_unicode=True, sort_keys=False), encoding="utf-8")
