from pregnancy_copilot.context_package import build_host_context_package
from pregnancy_copilot.response_style import build_response_style
from pregnancy_copilot.storage import PregnancyDataStore
from scripts.init_data_dir import initialize_data_dir
import yaml


def test_default_response_style_is_neutral_and_not_littlez_specific(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)

    package = build_host_context_package(
        store=store,
        user_message="今天有点担心糖耐。",
        intent="pregnancy_log",
        channel="agent_default",
    )

    style = package["response_style"]
    assert style["preset"] == "neutral_clinical"
    assert style["personalization_source"] == "default"
    combined = package["system_prompt"] + "\n" + "\n".join(style["instructions"])
    assert ("Little" + ".z") not in combined
    assert ("小" + "π") not in combined
    assert ("母体" + "服务器") not in combined
    assert "极客" not in combined
    assert "默认不要套用迁移样例中的个人化人设" in combined


def test_geek_ops_style_requires_explicit_profile_opt_in(tmp_path):
    initialize_data_dir(tmp_path)
    profile_path = tmp_path / "memory" / "profile.yaml"
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    profile["preferences"]["response_style"] = {
        "preset": "geek_ops",
        "enabled": True,
        "nickname": "孕妇用户",
        "baby_nickname": "胎儿",
        "custom_terms": {"body": "母体系统", "baby": "新硬件"},
    }
    profile_path.write_text(yaml.safe_dump(profile, allow_unicode=True, sort_keys=False), encoding="utf-8")

    style = build_response_style(PregnancyDataStore(tmp_path).load_profile())

    assert style["preset"] == "geek_ops"
    assert style["personalization_source"] == "profile.preferences.response_style"
    assert any("技术类比" in item for item in style["instructions"])
    assert any("孕妇用户" in item for item in style["instructions"])
    assert any("母体系统" in item for item in style["instructions"])
    assert ("Little" + ".z") not in "\n".join(style["instructions"])


def test_agent_soul_file_can_extend_style_without_becoming_default(tmp_path):
    initialize_data_dir(tmp_path)
    soul_path = tmp_path / "memory" / "agent_soul.md"
    soul_path.write_text("- 输出要短\n- 先给结论\n", encoding="utf-8")
    profile_path = tmp_path / "memory" / "profile.yaml"
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    profile["preferences"]["response_style"] = {
        "preset": "neutral_clinical",
        "enabled": True,
        "agent_soul_path": "memory/agent_soul.md",
    }
    profile_path.write_text(yaml.safe_dump(profile, allow_unicode=True, sort_keys=False), encoding="utf-8")

    package = build_host_context_package(
        store=PregnancyDataStore(tmp_path),
        user_message="今天记录一下体重。",
        intent="pregnancy_log",
        channel="agent_default",
    )

    assert package["response_style"]["agent_soul_excerpt"] == "- 输出要短\n- 先给结论"
    assert "- 输出要短" in package["system_prompt"]
