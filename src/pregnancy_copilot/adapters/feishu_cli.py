from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Sequence

from pregnancy_copilot.models import MessageEvent

from .base import MessageAdapter


CommandRunner = Callable[[Sequence[str]], str]


def run_command(command: Sequence[str]) -> str:
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    return completed.stdout


class FeishuCliAdapter(MessageAdapter):
    def __init__(self, runner: CommandRunner = run_command, profile: str | None = None):
        self.runner = runner
        self.profile = profile

    def receive_message(self, payload: dict) -> MessageEvent:
        return MessageEvent(
            message_id=payload.get("message_id") or payload.get("id") or "",
            timestamp=str(payload.get("timestamp") or payload.get("create_time") or ""),
            sender_id=payload.get("sender_id", ""),
            sender_role=payload.get("sender_role", "pregnant_user"),
            chat_type=payload.get("chat_type", "p2p"),
            text=payload.get("content", ""),
            source="feishu",
            chat_id=payload.get("chat_id"),
            event_id=payload.get("event_id"),
            message_type=payload.get("message_type"),
        )

    def send_reply(self, message: MessageEvent, text: str) -> None:
        command = self._command(
            [
                "im",
                "+messages-reply",
                "--as",
                "bot",
                "--message-id",
                message.message_id,
                "--text",
                text,
            ]
        )
        self.runner(command)

    def send_message(self, text: str, chat_id: str | None = None, user_id: str | None = None) -> None:
        if bool(chat_id) == bool(user_id):
            raise ValueError("Exactly one of chat_id or user_id is required.")

        command = self._command(["im", "+messages-send", "--as", "bot"])
        if chat_id:
            command.extend(["--chat-id", chat_id])
        else:
            command.extend(["--user-id", user_id or ""])
        command.extend(["--text", text])
        self.runner(command)

    def write_doc(self, title: str, content: str, folder_token: str | None = None) -> str:
        command = self._command(
            [
                "docs",
                "+create",
                "--as",
                "user",
                "--title",
                title,
                "--markdown",
                content,
            ]
        )
        if folder_token:
            command.extend(["--folder-token", folder_token])

        output = self.runner(command)
        if not output.strip():
            return ""
        data = json.loads(output)
        return data.get("document_id") or data.get("documentId") or data.get("url", "")

    def _command(self, args: list[str]) -> list[str]:
        if self.profile:
            return ["lark-cli", "--profile", self.profile, *args]
        return ["lark-cli", *args]
