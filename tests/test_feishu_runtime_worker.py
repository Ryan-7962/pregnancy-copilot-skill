import json

from pregnancy_copilot.feishu_runtime_worker import (
    load_seen_message_ids,
    parse_chat_messages_list,
    pending_user_messages,
    save_seen_message_ids,
)


def test_parse_chat_messages_list_extracts_user_message():
    output = json.dumps(
        {
            "ok": True,
            "data": {
                "messages": [
                    {
                        "chat_id": "oc_chat",
                        "content": "今天肚子有点紧",
                        "create_time": "2026-05-28 21:30",
                        "message_id": "om_001",
                        "message_position": "11",
                        "msg_type": "text",
                        "sender": {
                            "id": "ou_user",
                            "id_type": "open_id",
                            "sender_type": "user",
                        },
                    }
                ]
            },
        }
    )

    messages = parse_chat_messages_list(output)

    assert len(messages) == 1
    assert messages[0].message_id == "om_001"
    assert messages[0].sender_id == "ou_user"
    assert messages[0].text == "今天肚子有点紧"
    assert messages[0].message_position == 11


def test_pending_user_messages_skips_seen_and_bot_messages():
    output = json.dumps(
        {
            "data": {
                "messages": [
                    {
                        "chat_id": "oc_chat",
                        "content": "bot reply",
                        "message_id": "om_bot",
                        "message_position": "12",
                        "sender": {"id": "cli_bot", "id_type": "app_id", "sender_type": "app"},
                    },
                    {
                        "chat_id": "oc_chat",
                        "content": "seen",
                        "message_id": "om_seen",
                        "message_position": "13",
                        "sender": {"id": "ou_user", "id_type": "open_id", "sender_type": "user"},
                    },
                    {
                        "chat_id": "oc_chat",
                        "content": "new",
                        "message_id": "om_new",
                        "message_position": "14",
                        "sender": {"id": "ou_user", "id_type": "open_id", "sender_type": "user"},
                    },
                ]
            }
        }
    )

    messages = parse_chat_messages_list(output)
    pending = pending_user_messages(messages, {"om_seen"}, bot_app_id="cli_bot")

    assert [message.message_id for message in pending] == ["om_new"]


def test_seen_message_ids_round_trip(tmp_path):
    path = tmp_path / "seen.json"

    save_seen_message_ids(path, {"om_2", "om_1", ""})

    assert load_seen_message_ids(path) == {"om_1", "om_2"}
