from __future__ import annotations

from dataclasses import dataclass


COMMAND_MODES = {
    "#爸爸日记": "dad_diary",
    "#宝宝日记": "baby_diary",
    "#今日总结": "daily_summary",
    "#产检问题": "doctor_questions",
    "#备份": "backup",
    "#导出": "export",
}

PRIVACY_COMMANDS = {
    "#不同步": "private",
    "#只同步建议": "advice_only",
    "#可同步": "summary",
    "#完整同步": "full",
}


@dataclass
class MessageRoute:
    mode: str
    command: str | None
    privacy_override: str | None
    normalized_text: str


def route_message(text: str, sender_role: str = "pregnant_user", chat_type: str = "private") -> MessageRoute:
    stripped = text.strip()
    command = None
    privacy_override = None
    mode = default_mode(sender_role, chat_type)

    for prefix, value in {**COMMAND_MODES, **PRIVACY_COMMANDS}.items():
        if stripped.startswith(prefix):
            command = prefix
            stripped = stripped.removeprefix(prefix).strip()
            if prefix in COMMAND_MODES:
                mode = value
            else:
                privacy_override = value
            break

    return MessageRoute(mode=mode, command=command, privacy_override=privacy_override, normalized_text=stripped)


def default_mode(sender_role: str, chat_type: str) -> str:
    if sender_role == "partner":
        return "dad_mode"
    if chat_type in {"group", "chat"}:
        return "couple_coordination"
    return "pregnancy_qa"
