from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def evaluate_host_channel_blackbox(cases_path: str | Path, messages_path: str | Path) -> dict[str, Any]:
    cases = json.loads(Path(cases_path).read_text(encoding="utf-8"))["cases"]
    messages = load_messages(messages_path)
    results = []
    for case in cases:
        reply, context = find_reply_and_context_after_case(messages, case["id"])
        expect = case.get("expect", {})
        checks = evaluate_reply(reply, expect, evidence_context=context)
        no_reply_allowed = bool(expect.get("allow_no_reply")) and not reply
        if no_reply_allowed:
            checks = {"allow_no_reply": True}
        results.append(
            {
                "id": case["id"],
                "category": case.get("category"),
                "ok": no_reply_allowed or (bool(reply) and all(checks.values())),
                "reply_found": bool(reply),
                "checks": checks,
                "reply_excerpt": reply[:300] if reply else "",
            }
        )
    return {
        "ok": all(item["ok"] for item in results),
        "case_count": len(results),
        "results": results,
    }


def load_messages(messages_path: str | Path) -> list[dict[str, Any]]:
    data = json.loads(Path(messages_path).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        if "data" in data and isinstance(data["data"], dict):
            return data["data"].get("messages") or data["data"].get("items") or []
        return data.get("messages") or data.get("items") or []
    return data


def find_reply_after_case(messages: list[dict[str, Any]], case_id: str) -> str:
    reply, _context = find_reply_and_context_after_case(messages, case_id)
    return reply


def find_reply_and_context_after_case(messages: list[dict[str, Any]], case_id: str) -> tuple[str, str]:
    chronological = list(reversed(messages))
    latest_reply = ""
    latest_context = ""
    for index, message in enumerate(chronological):
        if case_id not in message_content(message):
            continue
        bounded_replies = []
        for candidate in chronological[index + 1 :]:
            if sender_type(candidate) == "user":
                break
            content = message_content(candidate)
            if sender_type(candidate) == "app" and not is_tool_noise(content):
                bounded_replies.append(content)
        if bounded_replies:
            tagged = [reply for reply in bounded_replies if case_id in reply]
            latest_reply = (tagged or bounded_replies)[-1]
            latest_context = "\n".join(bounded_replies)
    return latest_reply, latest_context


def evaluate_reply(reply: str, expect: dict[str, list[str]], evidence_context: str = "") -> dict[str, bool]:
    checks: dict[str, bool] = {}
    must_all = expect.get("must_contain_all") or []
    must_any = expect.get("must_contain_any") or []
    must_not = expect.get("must_not_contain_any") or []
    allow_forbidden = expect.get("allow_forbidden_if_contains_any") or []
    checks["must_contain_all"] = all(item in reply for item in must_all)
    checks["must_contain_any"] = True if not must_any else any(item in reply for item in must_any)
    has_forbidden = any(item in reply for item in must_not)
    evidence = f"{reply}\n{evidence_context}"
    has_allowing_evidence = bool(allow_forbidden) and any(item in evidence for item in allow_forbidden)
    checks["must_not_contain_any"] = (not has_forbidden) or has_allowing_evidence
    return checks


def message_content(message: dict[str, Any]) -> str:
    return str(message.get("content") or message.get("body", {}).get("content") or "")


def sender_type(message: dict[str, Any]) -> str:
    return str((message.get("sender") or {}).get("sender_type") or "")


def is_tool_noise(content: str) -> bool:
    prefixes = (
        "💻 terminal:",
        "🐍 execute_code:",
        "⚡ Interrupting",
        "Operation interrupted",
        "⏳ Retrying",
        "宿主调用结果：",
    )
    return content.startswith(prefixes)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate host Agent channel blackbox replies from exported chat messages.")
    parser.add_argument("--cases", default="examples/host_channel_blackbox_cases.json")
    parser.add_argument("--messages", required=True)
    args = parser.parse_args()

    result = evaluate_host_channel_blackbox(args.cases, args.messages)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
