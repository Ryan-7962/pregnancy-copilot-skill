from __future__ import annotations

from pathlib import Path
from typing import Any


DEFAULT_INSTRUCTIONS = [
    "默认不要套用迁移样例中的个人化人设、昵称或黑话。",
    "保持清晰、克制、结构化；先给结论，再给依据和下一步。",
    "医学内容必须以事实来源、当前有效数据和安全边界为先。",
]


def build_response_style(profile: dict[str, Any], data_root: str | Path | None = None) -> dict[str, Any]:
    preferences = profile.get("preferences") or {}
    config = preferences.get("response_style")
    if not isinstance(config, dict) or not config.get("enabled"):
        return {
            "preset": "neutral_clinical",
            "personalization_source": "default",
            "instructions": DEFAULT_INSTRUCTIONS,
        }

    preset = str(config.get("preset") or "neutral_clinical")
    if preset == "geek_ops":
        instructions = build_geek_ops_instructions(config)
    else:
        instructions = DEFAULT_INSTRUCTIONS

    result = {
        "preset": preset,
        "personalization_source": "profile.preferences.response_style",
        "instructions": instructions,
    }
    soul_excerpt = read_agent_soul_excerpt(config, data_root)
    if soul_excerpt:
        result["agent_soul_excerpt"] = soul_excerpt
        result["instructions"] = instructions + ["可参考用户提供的 agent_soul 摘要，但不得覆盖医学安全边界。"]
    return result


def build_geek_ops_instructions(config: dict[str, Any]) -> list[str]:
    nickname = config.get("nickname") or "孕妇用户"
    baby_nickname = config.get("baby_nickname") or "胎儿"
    custom_terms = config.get("custom_terms") if isinstance(config.get("custom_terms"), dict) else {}
    body_term = custom_terms.get("body") or "身体系统"
    baby_term = custom_terms.get("baby") or "胎儿发育系统"
    return [
        "用户已显式选择技术/运维风格；可以使用轻量技术类比帮助理解。",
        f"称呼孕妇为：{nickname}；称呼胎儿为：{baby_nickname}。",
        f"可把孕妇身体类比为：{body_term}；可把胎儿状态类比为：{baby_term}。",
        "技术类比只能服务于解释，不得替代医学事实、检查报告或医生建议。",
        "不要继承任何未写入本 profile 的私人昵称、医院、地点或家庭关系设定。",
    ]


def read_agent_soul_excerpt(config: dict[str, Any], data_root: str | Path | None) -> str:
    soul_path = config.get("agent_soul_path")
    if not soul_path or data_root is None:
        return ""
    path = Path(soul_path)
    if not path.is_absolute():
        path = Path(data_root) / path
    if not path.exists() or not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8").strip()
    return text[:1200]
