from __future__ import annotations

import os
import shlex

from pregnancy_copilot.llm import CommandLLMProvider
from pregnancy_copilot.triage import LLMTriageAdvisor


TRIAGE_LLM_COMMAND_ENV = "PREGNANCY_COPILOT_TRIAGE_LLM_COMMAND"
RESPONSE_LLM_COMMAND_ENV = "PREGNANCY_COPILOT_RESPONSE_LLM_COMMAND"


def build_triage_advisor_from_env():
    command = os.environ.get(TRIAGE_LLM_COMMAND_ENV, "").strip()
    if not command:
        return None
    return LLMTriageAdvisor(CommandLLMProvider(shlex.split(command)))


def build_response_provider_from_env():
    command = os.environ.get(RESPONSE_LLM_COMMAND_ENV, "").strip()
    if not command:
        return None
    return CommandLLMProvider(shlex.split(command))
