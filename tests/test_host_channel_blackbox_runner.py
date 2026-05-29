import json

from scripts.run_host_channel_blackbox_test import build_fetch_command, build_send_command, load_case_messages


def test_build_send_command_targets_chat_with_case_prefix():
    command = build_send_command(
        chat_id="oc_test",
        case_id="PCSKILL-R05-OGTT-DIET",
        message="下周要做糖耐。",
    )

    assert command[:4] == ["lark-cli", "im", "+messages-send", "--as"]
    assert "--chat-id" in command
    assert command[command.index("--chat-id") + 1] == "oc_test"
    text = command[command.index("--text") + 1]
    assert text.startswith("[PCSKILL-R05-OGTT-DIET]")
    assert "下周要做糖耐。" in text


def test_build_fetch_command_writes_json_messages():
    command = build_fetch_command(chat_id="oc_test", page_size=80)

    assert command == [
        "lark-cli",
        "im",
        "+chat-messages-list",
        "--as",
        "user",
        "--chat-id",
        "oc_test",
        "--page-size",
        "80",
        "--sort",
        "desc",
        "--format",
        "json",
    ]


def test_load_case_messages_filters_by_case_ids(tmp_path):
    cases_path = tmp_path / "cases.json"
    cases_path.write_text(
        json.dumps(
            {
                "cases": [
                    {"id": "PCSKILL-R01-GREEN", "message": "m1"},
                    {"id": "PCSKILL-R08-GENERAL", "message": "m8"},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    cases = load_case_messages(cases_path, case_ids=["PCSKILL-R08-GENERAL"])

    assert cases == [{"id": "PCSKILL-R08-GENERAL", "message": "m8"}]
