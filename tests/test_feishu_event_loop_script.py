import sys

from scripts.run_feishu_event_loop import (
    build_consume_command,
    build_runtime_response_provider,
    build_runtime_triage_advisor,
    ensure_data_root_initialized,
)


def test_build_consume_command_inserts_profile_after_lark_cli_binary():
    command = build_consume_command(max_events=1, timeout="15s", profile="<lark-profile>")

    assert command[:6] == ["lark-cli", "--profile", "<lark-profile>", "event", "consume", "im.message.receive_v1"]


def test_ensure_data_root_initialized_creates_profile_before_event_loop(tmp_path):
    root = tmp_path / "pregnancy-data"

    store = ensure_data_root_initialized(root)

    assert (root / "memory" / "profile.yaml").exists()
    assert (root / "events").is_dir()
    assert store.root == root


def test_build_runtime_triage_advisor_reads_env_command(monkeypatch):
    monkeypatch.setenv(
        "PREGNANCY_COPILOT_TRIAGE_LLM_COMMAND",
        f"{sys.executable!r} -c \"print('{{\\\"risk_level\\\": \\\"yellow\\\", \\\"reason\\\": \\\"semantic\\\"}}')\"",
    )

    advisor = build_runtime_triage_advisor()

    assert advisor is not None


def test_build_runtime_triage_advisor_returns_none_without_env(monkeypatch):
    monkeypatch.delenv("PREGNANCY_COPILOT_TRIAGE_LLM_COMMAND", raising=False)

    assert build_runtime_triage_advisor() is None


def test_build_runtime_response_provider_reads_env_command(monkeypatch):
    monkeypatch.setenv(
        "PREGNANCY_COPILOT_RESPONSE_LLM_COMMAND",
        f"{sys.executable!r} -c \"print('reply')\"",
    )

    assert build_runtime_response_provider() is not None


def test_build_runtime_response_provider_returns_none_without_env(monkeypatch):
    monkeypatch.delenv("PREGNANCY_COPILOT_RESPONSE_LLM_COMMAND", raising=False)

    assert build_runtime_response_provider() is None
