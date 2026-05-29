from pregnancy_copilot.adapters.feishu_mock import MockFeishuAdapter


def test_mock_feishu_adapter_normalizes_payload_and_records_outputs():
    adapter = MockFeishuAdapter()

    message = adapter.receive_message(
        {
            "message_id": "msg-001",
            "timestamp": "2026-05-05T08:30:00+08:00",
            "sender_id": "user-001",
            "sender_role": "pregnant_user",
            "chat_type": "private",
            "text": "今天肚子有点紧",
        }
    )
    adapter.send_reply(message, "先记录一下频率。")
    doc_id = adapter.write_doc("W20+0｜心情：稳定｜宝宝状态：继续成长", "# 内容")

    assert message.source == "feishu"
    assert adapter.sent_replies == [("msg-001", "先记录一下频率。")]
    assert doc_id == "mock-doc-001"
    assert adapter.docs[doc_id]["title"].startswith("W20+0")
