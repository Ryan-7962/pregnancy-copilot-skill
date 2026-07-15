import pytest

from scripts.process_channel_message import normalize_channel_payload, run_channel_message
from tests.helpers import make_profile_ready


def test_process_channel_message_accepts_agent_default_like_payload(tmp_path):
    make_profile_ready(tmp_path)
    result = run_channel_message(
        tmp_path,
        {
            "channel": "agent_default",
            "chat_id": "pregnancy-default-chat",
            "sender_id": "pregnant-user",
            "text": "今天肚子有点紧，休息后好了，没有流血也没有流水",
            "timestamp": "2026-05-16T20:00:00+08:00",
        },
    )

    assert result["ok"] is True
    assert result["host_request"]["channel"] == "agent_default"
    assert result["host_request"]["conversation_id"] == "pregnancy-default-chat"
    assert result["handled"] is True
    assert result["intent"] == "medical_triage"
    assert result["context_package"]["channel"] == "agent_default"
    assert (tmp_path / "inbox" / "raw_agent_default_messages" / "2026-05-16.md").exists()


def test_process_channel_message_returns_context_only_for_general_chat(tmp_path):
    make_profile_ready(tmp_path)
    result = run_channel_message(
        tmp_path,
        {
            "channel": "hermes",
            "chat_id": "pregnancy-window",
            "sender_id": "pregnant-user",
            "text": "推荐一首歌",
        },
    )

    assert result["handled"] is True
    assert result["reply_text"] == ""
    assert result["intent"] == "pregnancy_context"
    assert result["context_package"] is not None
    assert not (tmp_path / "events" / "events.jsonl").exists()


def test_normalize_channel_payload_requires_text_and_sender():
    with pytest.raises(ValueError, match="Missing message text"):
        normalize_channel_payload({"sender_id": "pregnant-user"})
    with pytest.raises(ValueError, match="Missing sender id"):
        normalize_channel_payload({"text": "今天肚子有点紧"})
