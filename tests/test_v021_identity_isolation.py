import pytest
import yaml

from pregnancy_copilot.host_runtime import HostMessageRequest, process_host_message
from pregnancy_copilot.identity import IdentityBindingError, IdentityEndpoint, IdentityRegistry
from scripts.process_channel_message import run_channel_message
from tests.helpers import make_profile_ready


def request(sender_id: str, *, pregnancy_id: str | None = None, text: str = "今天体重 50kg"):
    return HostMessageRequest(
        text=text,
        sender_id=sender_id,
        conversation_id=f"chat-{sender_id}",
        channel="agent_default",
        timestamp="2026-07-15T10:00:00+08:00",
        message_id=f"msg-{sender_id}",
        pregnancy_id=pregnancy_id,
    )


def test_legacy_single_identity_root_rejects_a_second_pregnant_user(tmp_path):
    make_profile_ready(tmp_path)
    process_host_message(request("user-a"), data_root=tmp_path)

    with pytest.raises(IdentityBindingError, match="not bound"):
        process_host_message(request("user-b"), data_root=tmp_path)

    events = (tmp_path / "events" / "events.jsonl").read_text(encoding="utf-8")
    assert "user-a" in events
    assert "user-b" not in events


def test_two_pregnancy_identities_use_separate_data_roots(tmp_path):
    process_host_message(
        request("user-a", pregnancy_id="pregnancy-a", text="建档：称呼：用户A，LMP 2026-05-01"),
        data_root=tmp_path,
    )
    process_host_message(
        request("user-b", pregnancy_id="pregnancy-b", text="建档：称呼：用户B，LMP 2026-06-01"),
        data_root=tmp_path,
    )

    root_a = tmp_path / "identities" / "pregnancy-a"
    root_b = tmp_path / "identities" / "pregnancy-b"
    profile_a = yaml.safe_load((root_a / "memory" / "profile.yaml").read_text(encoding="utf-8"))
    profile_b = yaml.safe_load((root_b / "memory" / "profile.yaml").read_text(encoding="utf-8"))
    assert root_a != root_b
    assert profile_a["display_name"] == "用户A"
    assert profile_b["display_name"] == "用户B"
    assert profile_a["last_menstrual_period"] == "2026-05-01"
    assert profile_b["last_menstrual_period"] == "2026-06-01"


def test_unbound_endpoint_cannot_claim_existing_identity(tmp_path):
    process_host_message(
        request("user-a", pregnancy_id="pregnancy-a", text="建档：LMP 2026-05-01"),
        data_root=tmp_path,
    )

    with pytest.raises(IdentityBindingError, match="not bound"):
        process_host_message(request("attacker", pregnancy_id="pregnancy-a"), data_root=tmp_path)


def test_explicitly_authorized_second_endpoint_can_use_same_identity(tmp_path):
    process_host_message(
        request("user-a", pregnancy_id="pregnancy-a", text="建档：LMP 2026-05-01"),
        data_root=tmp_path,
    )
    registry = IdentityRegistry(tmp_path)
    registry.bind_endpoint(
        "pregnancy-a",
        IdentityEndpoint(channel="other_channel", conversation_id="chat-user-a-mobile", sender_id="user-a-mobile"),
    )

    result = process_host_message(
        HostMessageRequest(
            text="怀孕可以坐飞机吗？",
            sender_id="user-a-mobile",
            conversation_id="chat-user-a-mobile",
            channel="other_channel",
            timestamp="2026-07-15T11:00:00+08:00",
            message_id="msg-mobile",
            pregnancy_id="pregnancy-a",
        ),
        data_root=tmp_path,
    )

    assert result.handled is True
    assert result.context_package is not None


def test_generic_channel_bridge_uses_host_configured_identity_not_payload_identity(tmp_path):
    payload = {
        "channel": "agent_default",
        "chat_id": "chat-user-a",
        "sender_id": "user-a",
        "text": "建档：LMP 2026-05-01",
        "pregnancy_id": "attacker-controlled",
    }

    result = run_channel_message(tmp_path, payload, pregnancy_id="pregnancy-a")

    assert result["host_request"]["pregnancy_id"] == "pregnancy-a"
    assert (tmp_path / "identities" / "pregnancy-a" / "memory" / "profile.yaml").exists()
    assert not (tmp_path / "identities" / "attacker-controlled").exists()
