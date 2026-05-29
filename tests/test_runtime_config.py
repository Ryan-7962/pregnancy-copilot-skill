import os
import shlex
import sys

from pregnancy_copilot.runtime_config import build_response_provider_from_env, build_triage_advisor_from_env


def test_build_triage_advisor_from_env_returns_none_without_command(monkeypatch):
    monkeypatch.delenv("PREGNANCY_COPILOT_TRIAGE_LLM_COMMAND", raising=False)

    assert build_triage_advisor_from_env() is None


def test_build_triage_advisor_from_env_uses_command_provider(monkeypatch):
    monkeypatch.setenv(
        "PREGNANCY_COPILOT_TRIAGE_LLM_COMMAND",
        f"{shlex.quote(sys.executable)} -c \"import json; print(json.dumps({{'risk_level':'yellow','reason':'semantic'}}))\"",
    )

    advisor = build_triage_advisor_from_env()
    result = advisor.assess("今天不太舒服", rule_result=_green_result())

    assert result.risk_level == "yellow"
    assert result.reason == "semantic"


def test_build_response_provider_from_env_returns_none_without_command(monkeypatch):
    monkeypatch.delenv("PREGNANCY_COPILOT_RESPONSE_LLM_COMMAND", raising=False)

    assert build_response_provider_from_env() is None


def test_build_response_provider_from_env_uses_command_provider(monkeypatch):
    monkeypatch.setenv(
        "PREGNANCY_COPILOT_RESPONSE_LLM_COMMAND",
        f"{shlex.quote(sys.executable)} -c \"import sys; print('reply:' + sys.stdin.read()[:5])\"",
    )

    provider = build_response_provider_from_env()

    assert provider.generate("hello world").strip() == "reply:hello"


def _green_result():
    from pregnancy_copilot.models import TriageResult

    return TriageResult(risk_level="green", reason="rule")
