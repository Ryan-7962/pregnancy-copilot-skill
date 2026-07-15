from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
import yaml

from pregnancy_copilot.data_init import initialize_data_dir
from pregnancy_copilot.host_runtime import HostMessageRequest, process_host_message
from pregnancy_copilot.medical_state import record_medical_observation
from pregnancy_copilot.storage import PregnancyDataStore


def run_single_user_acceptance(data_root: str | Path) -> dict[str, Any]:
    root = Path(data_root)
    initialize_data_dir(root)
    store = PregnancyDataStore(root)
    profile = store.load_profile()
    make_profile_ready(root)

    general = process_host_message(
        HostMessageRequest(
            text="明天天气怎么样，推荐一首歌",
            sender_id="pregnant-user",
            sender_role="pregnant_user",
            conversation_id="pregnancy-window",
            channel="acceptance",
            timestamp="2026-05-16T09:00:00+08:00",
        ),
        data_root=root,
    )
    symptom = process_host_message(
        HostMessageRequest(
            text="今天肚子有点紧，休息后好了，没有流血也没有流水",
            sender_id="pregnant-user",
            sender_role="pregnant_user",
            conversation_id="pregnancy-window",
            channel="acceptance",
            timestamp="2026-05-16T09:01:00+08:00",
        ),
        data_root=root,
    )
    first_state = record_medical_observation(
        store,
        {
            "metric_key": "cervical_length",
            "display_name": "宫颈管长度",
            "value": 29,
            "unit": "mm",
            "measured_at": "2026-05-08",
            "status": "watch",
            "interpretation": "需随访。",
        },
    )
    second_state = record_medical_observation(
        store,
        {
            "metric_key": "cervical_length",
            "display_name": "宫颈管长度",
            "value": 31,
            "unit": "mm",
            "measured_at": "2026-05-16",
            "status": "normal",
            "interpretation": "本次记录刷新旧值。",
        },
    )
    current_metric = second_state["metrics"]["cervical_length"]["current"]
    previous_values = second_state["metrics"]["cervical_length"]["previous_values"]

    checks = {
        "pregnant_user_default": profile["privacy"]["default_privacy_level"] == "summary",
        "partner_share_disabled_by_default": profile["preferences"].get("partner_share_default") == "private"
        and profile["preferences"].get("husband_share_default") == "private",
        "general_chat_uses_minimal_context": general.handled is True
        and general.intent == "pregnancy_context"
        and general.context_package is not None
        and general.risk_level == "not_applicable",
        "pregnancy_symptom_has_context_package": symptom.handled is True
        and symptom.intent == "medical_triage"
        and symptom.context_package is not None,
        "medical_state_uses_latest_value": current_metric["value"] == 31
        and current_metric["measured_at"] == "2026-05-16",
        "older_value_is_superseded": bool(previous_values)
        and previous_values[0]["value"] == 29
        and previous_values[0]["effective_status"] == "superseded",
    }
    return {
        "ok": all(checks.values()),
        "checks": checks,
        "general_chat": {
            "handled": general.handled,
            "intent": general.intent,
            "context_package": general.context_package,
        },
        "pregnancy_symptom": {
            "handled": symptom.handled,
            "intent": symptom.intent,
            "risk_level": symptom.risk_level,
            "has_context_package": symptom.context_package is not None,
        },
        "medical_state": {
            "current_value": f"{current_metric['value']}{current_metric.get('unit', '')}",
            "previous_values": [
                {
                    "value": item.get("value"),
                    "unit": item.get("unit"),
                    "effective_status": item.get("effective_status"),
                }
                for item in previous_values
            ],
        },
        "paths": {
            "data_root": root.as_posix(),
            "current_context": (root / "memory" / "current_context.md").as_posix(),
            "current_medical_state": (root / "memory" / "current_medical_state.yaml").as_posix(),
        },
    }


def make_profile_ready(data_root: str | Path) -> None:
    root = initialize_data_dir(data_root)
    profile_path = root / "memory" / "profile.yaml"
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    profile.update(
        profile_name="Acceptance Pregnancy Profile",
        display_name="验收用户",
        baby_nickname="验收宝宝",
        current_gestational_age="23w1d",
    )
    profile_path.write_text(yaml.safe_dump(profile, allow_unicode=True, sort_keys=False), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the v0.1 pregnant-user-first acceptance checks.")
    parser.add_argument("--data-root", required=True)
    args = parser.parse_args()

    result = run_single_user_acceptance(args.data_root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
