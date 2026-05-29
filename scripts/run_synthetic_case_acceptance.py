from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from pregnancy_copilot.data_init import initialize_data_dir

try:
    from scripts.process_channel_message import run_channel_message
except ModuleNotFoundError:
    from process_channel_message import run_channel_message


DEFAULT_CASES_PATH = Path("examples/synthetic_cases/pregnancy_synthetic_cases.json")


def run_synthetic_case_acceptance(
    data_root: str | Path,
    cases_path: str | Path = DEFAULT_CASES_PATH,
    sender_id: str = "pregnant-user-synthetic",
    conversation_id: str = "synthetic-feishu-p2p",
) -> dict[str, Any]:
    data_root = Path(data_root)
    make_profile_ready(data_root)
    cases_path = Path(cases_path)
    suite = json.loads(cases_path.read_text(encoding="utf-8"))
    results = []
    for case in suite["cases"]:
        payload = {
            "channel": case.get("channel", "agent_default"),
            "chat_id": conversation_id,
            "sender_id": sender_id,
            "text": case["message"],
            "timestamp": case["timestamp"],
        }
        actual = run_channel_message(data_root, payload)
        expected = case["expected"]
        checks = {
            "handled": actual["handled"] == expected["handled"],
            "intent": actual["intent"] == expected["intent"],
            "triage_required": actual["triage_required"] == expected["triage_required"],
            "risk_level": actual["risk_level"] == expected["risk_level"],
            "host_action_type": actual["host_action"]["type"] == expected["host_action_type"],
        }
        if actual["handled"]:
            checks["context_package_present"] = actual["context_package"] is not None
            checks["raw_source_written"] = bool(actual["artifacts"].get("raw_source_path"))
        else:
            checks["context_package_absent"] = actual["context_package"] is None
            checks["no_event_written"] = actual["event"] is None
        results.append(
            {
                "id": case["id"],
                "ok": all(checks.values()),
                "checks": checks,
                "actual": {
                    "handled": actual["handled"],
                    "intent": actual["intent"],
                    "triage_required": actual["triage_required"],
                    "risk_level": actual["risk_level"],
                    "host_action_type": actual["host_action"]["type"],
                },
            }
        )
    return {
        "ok": all(result["ok"] for result in results),
        "cases_path": str(cases_path),
        "data_root": str(data_root),
        "privacy_note": suite.get("privacy_note", ""),
        "case_count": len(results),
        "results": results,
    }


def make_profile_ready(data_root: str | Path) -> None:
    root = initialize_data_dir(data_root)
    profile_path = root / "memory" / "profile.yaml"
    profile_text = profile_path.read_text(encoding="utf-8")
    replacements = {
        'profile_name: "Example Pregnancy Profile"': 'profile_name: "Synthetic Pregnancy Profile"',
        'display_name: "孕妇"': 'display_name: "合成测试用户"',
        'baby_nickname: "宝宝"': 'baby_nickname: "合成测试宝宝"',
        'current_gestational_age: "20w0d"': 'current_gestational_age: "23w1d"',
        'name: "示例医院"': 'name: "合成测试医院"',
    }
    for old, new in replacements.items():
        profile_text = profile_text.replace(old, new)
    profile_path.write_text(profile_text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run privacy-safe synthetic pregnancy cases through Host Runtime.")
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--cases-path", default=str(DEFAULT_CASES_PATH))
    parser.add_argument("--sender-id", default="pregnant-user-synthetic")
    parser.add_argument("--conversation-id", default="synthetic-feishu-p2p")
    args = parser.parse_args()

    result = run_synthetic_case_acceptance(
        data_root=args.data_root,
        cases_path=args.cases_path,
        sender_id=args.sender_id,
        conversation_id=args.conversation_id,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
