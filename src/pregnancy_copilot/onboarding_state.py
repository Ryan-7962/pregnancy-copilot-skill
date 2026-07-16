from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Any

import yaml

from .storage import PregnancyDataStore, SCHEMA_VERSION, atomic_write_text


DEFAULT_TUTORIAL_TOPICS = (
    "welcome_and_scope",
    "minimum_profile",
    "medical_truth",
    "memory_and_privacy",
    "records_and_controls",
    "daily_and_calendar",
    "external_content_audit",
)

TUTORIAL_NUDGES = {
    "welcome_and_scope": (
        "我是你的孕期助手。身体不适、报告、用药、饮食、运动、情绪、产检准备和日常生活都可以和我聊。"
    ),
    "minimum_profile": "为了结合你的真实孕周回答，请先告诉我末次月经、预产期，或带日期的当前孕周，知道其中一项即可。",
    "medical_truth": "发送报告时尽量保留检查日期、数值、单位和医生结论；不知道的内容直接写未知，我不会替你补全。",
    "memory_and_privacy": (
        "长期档案保存在本地 pregnancy-data；聊天内容是否经过宿主模型或消息平台，仍取决于你使用的 Agent 和通道。"
    ),
    "records_and_controls": "普通聊天不会自动变成已确认医学事实。你随时可以说“这条不记录”或“跳过教程”。",
    "daily_and_calendar": (
        "我可以整理每日孕期日志、产检计划和检查前提醒；需要时告诉我“开启产检提醒”，由你的 Agent 或系统定时调用。"
    ),
    "external_content_audit": (
        "看到小红书里拿不准、想讨论或想留存的孕期内容，可以直接把链接发给我。"
        "我会区分帖子原话、个人经验、商业内容和可核实证据，再结合你的档案回答。"
    ),
}


@dataclass(frozen=True)
class MessageControls:
    record_mode: str = "default"
    dismiss_tutorial: bool = False
    resume_tutorial: bool = False
    daily_summary_enabled: bool | None = None
    prenatal_reminders_enabled: bool | None = None
    reminder_lead_days: int | None = None
    xhs_video_transcription: str | None = None
    external_media_retention: bool | None = None


def default_onboarding_state() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "pregnancy_mode": "pending",
        "tutorial_status": "in_progress",
        "interaction_count": 0,
        "completed_topics": [],
        "pending_topics": list(DEFAULT_TUTORIAL_TOPICS),
        "last_prompted_topic": None,
        "last_prompted_at": None,
        "tutorial_dismissed": False,
        "preferences": {
            "daily_summary_enabled": True,
            "prenatal_reminders_enabled": False,
            "reminder_lead_days": 1,
            "xhs_video_transcription": "ask",
            "external_media_retention": False,
        },
    }


def read_onboarding_state(store: PregnancyDataStore) -> dict[str, Any]:
    path = store.root / "memory" / "onboarding_state.yaml"
    if not path.exists():
        state = default_onboarding_state()
        atomic_write_text(path, yaml.safe_dump(state, allow_unicode=True, sort_keys=False))
        return state
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return normalize_onboarding_state(payload)


def advance_onboarding_state(
    store: PregnancyDataStore,
    *,
    prompted_topic: str | None = None,
    profile_ready: bool = False,
    pregnancy_mode: str | None = None,
    dismiss_tutorial: bool = False,
    resume_tutorial: bool = False,
    interaction_timestamp: str | None = None,
    preference_updates: dict[str, Any] | None = None,
    increment_interaction: bool = True,
) -> dict[str, Any]:
    with store.transaction_lock("onboarding-state"):
        state = read_onboarding_state(store)
        if increment_interaction:
            state["interaction_count"] += 1

        completed = list(state["completed_topics"])
        if profile_ready and "minimum_profile" not in completed:
            completed.append("minimum_profile")
        if prompted_topic in DEFAULT_TUTORIAL_TOPICS and prompted_topic not in completed:
            completed.append(prompted_topic)
            state["last_prompted_topic"] = prompted_topic
            state["last_prompted_at"] = interaction_timestamp or datetime.now(timezone.utc).astimezone().isoformat()

        state["completed_topics"] = [topic for topic in DEFAULT_TUTORIAL_TOPICS if topic in completed]
        state["pending_topics"] = [topic for topic in DEFAULT_TUTORIAL_TOPICS if topic not in completed]

        if pregnancy_mode in {"pending", "active"}:
            state["pregnancy_mode"] = pregnancy_mode
        if dismiss_tutorial:
            state["tutorial_dismissed"] = True
            state["tutorial_status"] = "dismissed"
        elif resume_tutorial:
            state["tutorial_dismissed"] = False
            state["tutorial_status"] = "in_progress" if state["pending_topics"] else "complete"
        elif state["tutorial_dismissed"]:
            state["tutorial_status"] = "dismissed"
        else:
            state["tutorial_status"] = "complete" if not state["pending_topics"] else "in_progress"

        if preference_updates:
            for key in (
                "daily_summary_enabled",
                "prenatal_reminders_enabled",
                "reminder_lead_days",
                "xhs_video_transcription",
                "external_media_retention",
            ):
                if key in preference_updates:
                    state["preferences"][key] = preference_updates[key]

        path = store.root / "memory" / "onboarding_state.yaml"
        atomic_write_text(path, yaml.safe_dump(state, allow_unicode=True, sort_keys=False))
        return state


def select_tutorial_nudge(state: dict[str, Any], profile_ready: bool) -> dict[str, str] | None:
    normalized = normalize_onboarding_state(state)
    if normalized["tutorial_dismissed"] or normalized["tutorial_status"] in {"dismissed", "complete"}:
        return None
    for topic in normalized["pending_topics"]:
        if topic == "minimum_profile" and profile_ready:
            continue
        return {"topic": topic, "text": TUTORIAL_NUDGES[topic]}
    return None


def parse_message_controls(text: str) -> MessageControls:
    compact = " ".join(text.strip().split())
    no_record = compact == "仅本次" or compact.startswith("仅本次：") or any(
        phrase in compact
        for phrase in (
            "这条不记录",
            "不要记录这条",
            "只回答不记录",
            "仅本次回答，不要保存",
            "#不记录",
        )
    )
    daily_summary_enabled = None
    if any(phrase in compact for phrase in ("开启每日总结", "打开每日总结", "启用每日总结")):
        daily_summary_enabled = True
    elif any(phrase in compact for phrase in ("关闭每日总结", "停用每日总结")):
        daily_summary_enabled = False
    prenatal_reminders_enabled = None
    if any(phrase in compact for phrase in ("开启产检提醒", "打开产检提醒", "启用产检提醒")):
        prenatal_reminders_enabled = True
    elif any(phrase in compact for phrase in ("关闭产检提醒", "停用产检提醒")):
        prenatal_reminders_enabled = False
    lead_match = re.search(r"提前\s*(\d{1,2})\s*天", compact)
    reminder_lead_days = int(lead_match.group(1)) if lead_match else None
    xhs_video_transcription = None
    if any(phrase in compact for phrase in ("小红书视频以后都转写", "小红书视频自动转写")):
        xhs_video_transcription = "always"
    elif any(phrase in compact for phrase in ("不要转写小红书视频", "关闭小红书视频转写")):
        xhs_video_transcription = "never"
    elif any(phrase in compact for phrase in ("小红书视频每次先问我", "小红书视频转写前询问")):
        xhs_video_transcription = "ask"
    external_media_retention = None
    if any(phrase in compact for phrase in ("保留外部内容原图", "保留小红书原图")):
        external_media_retention = True
    elif any(phrase in compact for phrase in ("外部内容识别后删除原图", "小红书识别后删除原图")):
        external_media_retention = False
    return MessageControls(
        record_mode="no_record" if no_record else "default",
        dismiss_tutorial=any(phrase in compact for phrase in ("跳过教程", "关闭教程", "不用再介绍")),
        resume_tutorial=any(phrase in compact for phrase in ("继续教程", "恢复教程")),
        daily_summary_enabled=daily_summary_enabled,
        prenatal_reminders_enabled=prenatal_reminders_enabled,
        reminder_lead_days=reminder_lead_days,
        xhs_video_transcription=xhs_video_transcription,
        external_media_retention=external_media_retention,
    )


def normalize_onboarding_state(payload: dict[str, Any]) -> dict[str, Any]:
    state = default_onboarding_state()
    if payload.get("schema_version") == SCHEMA_VERSION:
        for key in (
            "pregnancy_mode",
            "tutorial_status",
            "interaction_count",
            "last_prompted_topic",
            "last_prompted_at",
            "tutorial_dismissed",
        ):
            if key in payload:
                state[key] = payload[key]
        completed = payload.get("completed_topics") or []
        state["completed_topics"] = [topic for topic in DEFAULT_TUTORIAL_TOPICS if topic in completed]
        state["pending_topics"] = [topic for topic in DEFAULT_TUTORIAL_TOPICS if topic not in state["completed_topics"]]
        preferences = payload.get("preferences") or {}
        state["preferences"].update(
            {key: value for key, value in preferences.items() if key in state["preferences"]}
        )
    return state
