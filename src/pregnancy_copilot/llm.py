from __future__ import annotations

import subprocess
from typing import Protocol


class LLMProvider(Protocol):
    def generate(self, prompt: str) -> str:
        pass


class NullLLMProvider:
    def generate(self, prompt: str) -> str:
        return ""


class CommandLLMProvider:
    def __init__(self, command: list[str], timeout_seconds: int = 30):
        self.command = command
        self.timeout_seconds = timeout_seconds

    def generate(self, prompt: str) -> str:
        try:
            result = subprocess.run(
                self.command,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return ""
        if result.returncode != 0:
            return ""
        return result.stdout
