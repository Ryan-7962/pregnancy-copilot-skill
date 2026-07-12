from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from pregnancy_copilot.data_init import initialize_data_dir
from pregnancy_copilot.host_runtime import HostMessageRequest, process_host_message
from pregnancy_copilot.medical_state import record_medical_observation
from pregnancy_copilot.storage import PregnancyDataStore


def run_host_runtime_acceptance(
    data_root: str | Path,
    channel: str = "hermes",
    conversation_id: str = "pregnancy-window",
    sender_id: str = "pregnant-user",
) -> dict[str, Any]:
    data_root = Path(data_root)
    general_only_root = data_root.parent / f"{data_root.name}-general-only"

    make_profile_ready(data_root)
    general = process_host_message(
        HostMessageRequest(
            text="推荐一首歌",
            sender_id=sender_id,
            sender_role="pregnant_user",
            conversation_id=conversation_id,
            channel=channel,
            timestamp="2026-05-16T10:00:00+08:00",
        ),
        data_root=data_root,
    )
    general_only = process_host_message(
        HostMessageRequest(
            text="推荐一首歌",
            sender_id=sender_id,
            sender_role="pregnant_user",
            conversation_id=conversation_id,
            channel=channel,
            timestamp="2026-05-16T09:59:00+08:00",
        ),
        data_root=general_only_root,
    )

    symptom = process_host_message(
        HostMessageRequest(
            text="今天肚子有点紧，休息后好了，没有流血也没有流水",
            sender_id=sender_id,
            sender_role="pregnant_user",
            conversation_id=conversation_id,
            channel=channel,
            timestamp="2026-05-16T10:01:00+08:00",
        ),
        data_root=data_root,
    )

    daily_log = process_host_message(
        HostMessageRequest(
            text="今天体重 50.8kg，早餐吃了鸡蛋牛奶，晚上散步 20 分钟",
            sender_id=sender_id,
            sender_role="pregnant_user",
            conversation_id=conversation_id,
            channel=channel,
            timestamp="2026-05-16T10:02:00+08:00",
        ),
        data_root=data_root,
    )

    store = PregnancyDataStore(data_root)
    record_medical_observation(
        store,
        {
            "metric_key": "cervical_length",
            "display_name": "宫颈管长度",
            "value": 29,
            "unit": "mm",
            "measured_at": "2026-05-08",
            "status": "watch",
            "interpretation": "高于 25mm 阈值，但需要随访。",
        },
    )
    medical_state = record_medical_observation(
        store,
        {
            "metric_key": "cervical_length",
            "display_name": "宫颈管长度",
            "value": 31,
            "unit": "mm",
            "measured_at": "2026-05-16",
            "status": "normal",
            "interpretation": "较 5.8 的 29mm 更新，当前值按 31mm 作为有效状态。",
        },
    )

    report_question = process_host_message(
        HostMessageRequest(
            text="这周复查报告写宫颈管 31mm，之前 29mm，现在应该按哪个判断？",
            sender_id=sender_id,
            sender_role="pregnant_user",
            conversation_id=conversation_id,
            channel=channel,
            timestamp="2026-05-16T10:03:00+08:00",
        ),
        data_root=data_root,
    )

    current_metric = medical_state["metrics"]["cervical_length"]["current"]
    previous_values = medical_state["metrics"]["cervical_length"]["previous_values"]
    checks = {
        "general_chat_not_handled": general.handled is False and general.context_package is None,
        "general_chat_host_action_pass_through": general.host_action.get("type") == "pass_through"
        and general.host_action.get("send_reply") is False
        and general.host_action.get("use_context_package") is False,
        "fresh_profile_triggers_onboarding": general_only.handled is True
        and general_only.intent == "profile_onboarding"
        and general_only.host_action.get("type") == "collect_profile"
        and "只保存在你指定的本地 pregnancy-data 目录" in general_only.reply_text
        and "请按产检报告原文录入" in general_only.reply_text
        and not (general_only_root / "events" / "events.jsonl").exists()
        and (general_only_root / "memory" / "profile.yaml").exists()
        and (general_only_root / "inbox" / f"raw_{channel}_messages" / "2026-05-16.md").exists(),
        "symptom_handled_with_context_package": symptom.handled is True and symptom.context_package is not None,
        "daily_log_without_visible_triage": daily_log.handled is True
        and daily_log.triage_required is False
        and daily_log.risk_level == "not_applicable",
        "latest_medical_state_wins": current_metric["value"] == 31 and current_metric["unit"] == "mm",
        "old_medical_state_superseded": previous_values
        and previous_values[0]["effective_status"] == "superseded",
        "report_question_context_uses_current_state": report_question.context_package is not None
        and report_question.context_package["current_medical_state"]["metrics"]["cervical_length"]["current"]["value"] == 31,
        "raw_inbox_written": (data_root / "inbox" / f"raw_{channel}_messages" / "2026-05-16.md").exists(),
        "events_written": (data_root / "events" / "events.jsonl").exists(),
        "current_context_written": (data_root / "memory" / "current_context.md").exists(),
        "current_medical_state_written": (data_root / "memory" / "current_medical_state.yaml").exists(),
    }
    return {
        "ok": all(checks.values()),
        "checks": checks,
        "host_contract": {
            "channel": channel,
            "conversation_id": conversation_id,
            "sender_id": sender_id,
            "general_chat": {
                "handled": general.handled,
                "intent": general.intent,
                "reply_text": general.reply_text,
                "host_action_type": general.host_action.get("type"),
                "send_reply": general.host_action.get("send_reply"),
                "use_context_package": general.host_action.get("use_context_package"),
            },
            "symptom": {
                "handled": symptom.handled,
                "intent": symptom.intent,
                "risk_level": symptom.risk_level,
                "has_context_package": symptom.context_package is not None,
            },
            "daily_log": {
                "handled": daily_log.handled,
                "intent": daily_log.intent,
                "risk_level": daily_log.risk_level,
                "triage_required": daily_log.triage_required,
            },
            "report_question": {
                "handled": report_question.handled,
                "intent": report_question.intent,
                "risk_level": report_question.risk_level,
                "current_cervical_length": "31mm",
            },
        },
        "paths": {
            "data_root": str(data_root),
            "events": str(data_root / "events" / "events.jsonl"),
            "current_context": str(data_root / "memory" / "current_context.md"),
            "current_medical_state": str(data_root / "memory" / "current_medical_state.yaml"),
        },
    }


def make_profile_ready(data_root: str | Path) -> None:
    root = initialize_data_dir(data_root)
    profile_path = root / "memory" / "profile.yaml"
    profile_text = profile_path.read_text(encoding="utf-8")
    replacements = {
        'profile_name: "Example Pregnancy Profile"': 'profile_name: "Acceptance Pregnancy Profile"',
        'display_name: "孕妇"': 'display_name: "验收用户"',
        'baby_nickname: "宝宝"': 'baby_nickname: "验收宝宝"',
        'current_gestational_age: "20w0d"': 'current_gestational_age: "23w1d"',
        'name: "示例医院"': 'name: "验收医院"',
    }
    for old, new in replacements.items():
        profile_text = profile_text.replace(old, new)
    profile_path.write_text(profile_text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Host Agent Runtime acceptance checks.")
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--channel", default="hermes")
    parser.add_argument("--conversation-id", default="pregnancy-window")
    parser.add_argument("--sender-id", default="pregnant-user")
    args = parser.parse_args()

    result = run_host_runtime_acceptance(
        data_root=args.data_root,
        channel=args.channel,
        conversation_id=args.conversation_id,
        sender_id=args.sender_id,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
