import json

from pregnancy_copilot.adapters.feishu_cli import FeishuCliAdapter


class FakeRunner:
    def __init__(self):
        self.commands = []

    def __call__(self, command):
        self.commands.append(command)
        if command[:3] == ["lark-cli", "docs", "+create"]:
            return json.dumps({"url": "https://docs.feishu.cn/docx/mock", "document_id": "docx_mock"})
        return json.dumps({"ok": True})


def test_receive_message_normalizes_lark_event_payload():
    adapter = FeishuCliAdapter(runner=FakeRunner())

    message = adapter.receive_message(
        {
            "event_id": "evt-001",
            "message_id": "om_001",
            "timestamp": "1777777777000",
            "sender_id": "ou_sender",
            "chat_id": "oc_chat",
            "chat_type": "p2p",
            "content": "今天肚子有点紧",
            "message_type": "text",
        }
    )

    assert message.message_id == "om_001"
    assert message.sender_id == "ou_sender"
    assert message.chat_id == "oc_chat"
    assert message.text == "今天肚子有点紧"
    assert message.source == "feishu"


def test_send_reply_uses_lark_cli_reply_command():
    runner = FakeRunner()
    adapter = FeishuCliAdapter(runner=runner)
    message = adapter.receive_message({"message_id": "om_001", "content": "hi"})

    adapter.send_reply(message, "收到，我先帮你记录。")

    assert runner.commands[-1] == [
        "lark-cli",
        "im",
        "+messages-reply",
        "--as",
        "bot",
        "--message-id",
        "om_001",
        "--text",
        "收到，我先帮你记录。",
    ]


def test_write_doc_uses_lark_cli_docs_create_command():
    runner = FakeRunner()
    adapter = FeishuCliAdapter(runner=runner)

    doc_id = adapter.write_doc("W20+0｜心情：稳定｜宝宝状态：继续成长", "# 内容", folder_token="fld_mock")

    assert doc_id == "docx_mock"
    assert runner.commands[-1] == [
        "lark-cli",
        "docs",
        "+create",
        "--as",
        "user",
        "--title",
        "W20+0｜心情：稳定｜宝宝状态：继续成长",
        "--markdown",
        "# 内容",
        "--folder-token",
        "fld_mock",
    ]


def test_adapter_inserts_profile_after_lark_cli_binary():
    runner = FakeRunner()
    adapter = FeishuCliAdapter(runner=runner, profile="<lark-profile>")
    message = adapter.receive_message({"message_id": "om_001", "content": "hi"})

    adapter.send_reply(message, "收到")

    assert runner.commands[-1][:4] == ["lark-cli", "--profile", "<lark-profile>", "im"]
