import json

from pregnancy_copilot.feishu_smoke import (
    build_list_messages_command,
    build_send_message_command,
    parse_send_message_output,
    summarize_smoke_outputs,
)


def test_build_send_message_command_targets_bot_p2p_open_id():
    command = build_send_message_command("ou_bot", "hello")

    assert command == [
        "lark-cli",
        "im",
        "+messages-send",
        "--as",
        "user",
        "--user-id",
        "ou_bot",
        "--text",
        "hello",
    ]


def test_smoke_commands_accept_lark_cli_profile():
    send_command = build_send_message_command("ou_bot", "hello", profile="<lark-profile>")
    list_command = build_list_messages_command("oc_chat", profile="<lark-profile>")

    assert send_command[:4] == ["lark-cli", "--profile", "<lark-profile>", "im"]
    assert list_command[:4] == ["lark-cli", "--profile", "<lark-profile>", "im"]


def test_parse_send_message_output_extracts_chat_and_message_id():
    payload = {
        "ok": True,
        "data": {
            "chat_id": "oc_chat",
            "message_id": "om_message",
        },
    }

    parsed = parse_send_message_output(json.dumps(payload))

    assert parsed == {"chat_id": "oc_chat", "message_id": "om_message"}


def test_summarize_smoke_outputs_reports_written_files_and_reply(tmp_path):
    (tmp_path / "events").mkdir()
    (tmp_path / "inbox" / "raw_feishu_messages").mkdir(parents=True)
    (tmp_path / "daily_logs").mkdir()
    (tmp_path / "memory").mkdir()
    (tmp_path / "events" / "events.jsonl").write_text(
        json.dumps(
            {
                "event_id": "evt-smoke",
                "risk_level": "green",
                "user_message_summary": "smoke marker",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "inbox" / "raw_feishu_messages" / "2026-05-06.md").write_text("smoke marker", encoding="utf-8")
    (tmp_path / "daily_logs" / "2026-05-06.md").write_text("green: 1", encoding="utf-8")
    (tmp_path / "memory" / "current_context.md").write_text("smoke marker", encoding="utf-8")

    report = summarize_smoke_outputs(
        data_root=tmp_path,
        marker="smoke marker",
        send_result={"chat_id": "oc_chat", "message_id": "om_message"},
        recent_messages=[
            {"content": "风险分级：绿色", "reply_to": "om_message", "sender": {"sender_type": "app"}},
        ],
    )

    assert report["ok"] is True
    assert report["risk_level"] == "green"
    assert report["local_files"]["events_jsonl"] is True
    assert report["local_files"]["raw_message"] is True
    assert report["bot_reply"]["ok"] is True
