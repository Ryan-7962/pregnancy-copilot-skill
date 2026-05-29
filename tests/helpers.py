from __future__ import annotations

from pathlib import Path

from pregnancy_copilot.data_init import initialize_data_dir


def make_profile_ready(data_root: str | Path) -> None:
    root = initialize_data_dir(data_root)
    profile_path = root / "memory" / "profile.yaml"
    profile_text = profile_path.read_text(encoding="utf-8")
    replacements = {
        'profile_name: "Example Pregnancy Profile"': 'profile_name: "Test Pregnancy Profile"',
        'display_name: "孕妇"': 'display_name: "测试用户"',
        'baby_nickname: "宝宝"': 'baby_nickname: "测试宝宝"',
        'current_gestational_age: "20w0d"': 'current_gestational_age: "23w1d"',
        'name: "示例医院"': 'name: "测试医院"',
    }
    for old, new in replacements.items():
        profile_text = profile_text.replace(old, new)
    profile_path.write_text(profile_text, encoding="utf-8")
