from pregnancy_copilot.host_runtime import HostMessageRequest, process_host_message
from scripts.process_channel_message import run_channel_message
from scripts.process_host_message import run_host_message
from tests.helpers import make_profile_ready


def test_host_action_tells_host_to_answer_general_chat_with_minimal_context(tmp_path):
    make_profile_ready(tmp_path)
    result = run_host_message(
        data_root=tmp_path,
        text="推荐一首歌",
        sender_id="pregnant-user",
        conversation_id="pregnancy-window",
        channel="hermes",
    )

    assert result["handled"] is True
    assert result["host_action"] == {
        "type": "answer_with_context_package",
        "send_reply": True,
        "use_context_package": True,
        "context_package_required": True,
        "target_channel": "hermes",
        "target_conversation_id": "pregnancy-window",
        "fallback_reply_text": "",
        "reason": "Pregnancy Copilot handled the message; host should answer using context_package and may use fallback_reply_text if no host LLM is available.",
    }


def test_host_action_tells_host_to_answer_with_context_package_for_pregnancy_message(tmp_path):
    make_profile_ready(tmp_path)
    result = run_channel_message(
        tmp_path,
        {
            "channel": "agent_default",
            "chat_id": "pregnancy-default-chat",
            "sender_id": "pregnant-user",
            "text": "今天肚子有点紧，休息后好了，没有流血也没有流水",
        },
    )

    assert result["handled"] is True
    assert result["host_action"]["type"] == "answer_with_context_package"
    assert result["host_action"]["send_reply"] is True
    assert result["host_action"]["use_context_package"] is True
    assert result["host_action"]["target_channel"] == "agent_default"
    assert result["host_action"]["target_conversation_id"] == "pregnancy-default-chat"
    assert result["host_action"]["fallback_reply_text"] == result["reply_text"]
    assert result["host_action"]["context_package_required"] is True


def test_process_host_message_result_exposes_host_action(tmp_path):
    make_profile_ready(tmp_path)
    result = process_host_message(
        HostMessageRequest(
            text="这个 B 超报告是什么意思",
            sender_id="pregnant-user",
            conversation_id="pregnancy-window",
            channel="hermes",
        ),
        data_root=tmp_path,
    )

    assert result.host_action["type"] == "answer_with_context_package"
    assert result.host_action["target_channel"] == "hermes"
