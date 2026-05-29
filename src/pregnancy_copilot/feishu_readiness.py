from __future__ import annotations

import json
import subprocess
from typing import Callable


CommandResult = tuple[int, str, str]
Runner = Callable[[list[str]], CommandResult]


def default_runner(command: list[str]) -> CommandResult:
    process = subprocess.run(command, capture_output=True, text=True, check=False)
    return process.returncode, process.stdout, process.stderr


MIN_LARK_CLI_VERSION = "1.0.23"


def check_feishu_readiness(runner: Runner = default_runner, profile: str | None = None) -> dict:
    doctor = run_command(runner, lark_command(["doctor"], profile=profile), parse_json=True)
    auth = run_command(runner, lark_command(["auth", "status"], profile=profile), parse_json=True)
    event_schema = run_command(runner, lark_command(["event", "schema", "im.message.receive_v1"], profile=profile))
    event_status = run_command(runner, lark_command(["event", "status"], profile=profile))

    scopes = parse_scope_set(auth.get("data", {}).get("scope", ""))
    schema_text = event_schema.get("stdout", "")

    capabilities = {
        "lark_cli_version": capability(
            ok=doctor["ok"] and version_at_least(extract_cli_version(doctor.get("data", {})), MIN_LARK_CLI_VERSION),
            action=f"升级 lark-cli 到 >= {MIN_LARK_CLI_VERSION}：npm update -g @larksuite/cli",
        ),
        "p2p_event_receive": capability(
            ok=event_schema["ok"] and "im:message.p2p_msg:readonly" in schema_text,
            action='在飞书开放平台启用 im.message.receive_v1，并开通 im:message.p2p_msg:readonly。',
        ),
        "group_event_receive": capability(
            ok=event_schema["ok"] and "im:message.group_msg:readonly" in schema_text,
            action="群聊测试需要额外确认群消息事件权限/控制台配置；当前 readiness 只确认 P2P 可用。",
        ),
        "user_send_message": capability(
            ok="im:message.send_as_user" in scopes,
            action='运行：lark-cli auth login --scope "im:message.send_as_user"',
        ),
        "user_create_chat": capability(
            ok="im:chat:create_by_user" in scopes,
            action='运行：lark-cli auth login --scope "im:chat:create_by_user"',
        ),
    }

    checks = {
        "doctor": doctor,
        "auth": auth,
        "event_schema": event_schema,
        "event_status": event_status,
    }
    required_for_p2p_test = [
        checks["doctor"]["ok"],
        capabilities["lark_cli_version"]["ok"],
        checks["auth"]["ok"],
        capabilities["p2p_event_receive"]["ok"],
        capabilities["user_send_message"]["ok"],
    ]
    return {
        "ok": all(required_for_p2p_test),
        "checks": checks,
        "capabilities": capabilities,
        "notes": [
            "v0.1 verified path is P2P bot chat.",
            "Group chat requires separate Feishu event/scopes validation before claiming support.",
        ],
    }


def run_command(runner: Runner, command: list[str], parse_json: bool = False) -> dict:
    code, stdout, stderr = runner(command)
    result = {
        "ok": code == 0,
        "command": command,
        "stdout": stdout.strip(),
        "stderr": stderr.strip(),
    }
    if code != 0:
        result["error"] = stderr.strip() or stdout.strip()
    if parse_json and stdout.strip():
        try:
            result["data"] = json.loads(stdout)
        except json.JSONDecodeError:
            result["ok"] = False
            result["error"] = "Expected JSON output but command returned non-JSON text."
            result["data"] = {}
    else:
        result["data"] = {}
    return result


def parse_scope_set(scope_text: str) -> set[str]:
    return {scope.strip() for scope in scope_text.split() if scope.strip()}


def capability(ok: bool, action: str) -> dict[str, str | bool]:
    return {"ok": ok, "action": "" if ok else action}


def lark_command(args: list[str], profile: str | None = None) -> list[str]:
    if profile:
        return ["lark-cli", "--profile", profile, *args]
    return ["lark-cli", *args]


def extract_cli_version(data: dict) -> str:
    for key in ("cli_version", "version", "cliVersion"):
        if data.get(key):
            return str(data[key])
    for check in data.get("checks") or []:
        if check.get("name") == "cli_version" and check.get("message"):
            return str(check["message"])
    return MIN_LARK_CLI_VERSION if data.get("ok") is True else "0.0.0"


def version_at_least(actual: str, minimum: str) -> bool:
    return parse_version(actual) >= parse_version(minimum)


def parse_version(value: str) -> tuple[int, int, int]:
    parts = []
    for raw in value.split(".")[:3]:
        digits = "".join(ch for ch in raw if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)
