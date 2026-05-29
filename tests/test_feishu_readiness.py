import json

from pregnancy_copilot.feishu_readiness import check_feishu_readiness


class FakeRunner:
    def __init__(self, outputs):
        self.outputs = outputs
        self.commands = []

    def __call__(self, command):
        self.commands.append(command)
        key = tuple(command)
        return self.outputs[key]


def result(code=0, stdout="", stderr=""):
    return code, stdout, stderr


def test_check_feishu_readiness_reports_p2p_ready_and_group_gap():
    runner = FakeRunner(
        {
            ("lark-cli", "doctor"): result(0, json.dumps({"ok": True, "cli_version": "1.0.23"})),
            ("lark-cli", "auth", "status"): result(
                0,
                json.dumps(
                    {
                        "tokenStatus": "valid",
                        "scope": "im:message.send_as_user im:chat:create_by_user im:message.p2p_msg:get_as_user",
                    }
                ),
            ),
            ("lark-cli", "event", "schema", "im.message.receive_v1"): result(
                0,
                "Required Scopes:\n  - im:message.p2p_msg:readonly\nRequired Console Events:\n  - im.message.receive_v1\n",
            ),
            ("lark-cli", "event", "status"): result(0, "Bus: not running"),
        }
    )

    report = check_feishu_readiness(runner=runner)

    assert report["ok"] is True
    assert report["checks"]["doctor"]["ok"] is True
    assert report["checks"]["auth"]["ok"] is True
    assert report["capabilities"]["p2p_event_receive"]["ok"] is True
    assert report["capabilities"]["user_send_message"]["ok"] is True
    assert report["capabilities"]["user_create_chat"]["ok"] is True
    assert report["capabilities"]["group_event_receive"]["ok"] is False
    assert "群消息事件" in report["capabilities"]["group_event_receive"]["action"]


def test_check_feishu_readiness_reports_missing_send_scope():
    runner = FakeRunner(
        {
            ("lark-cli", "doctor"): result(0, json.dumps({"ok": True, "cli_version": "1.0.23"})),
            ("lark-cli", "auth", "status"): result(
                0,
                json.dumps({"tokenStatus": "valid", "scope": "im:message.p2p_msg:get_as_user"}),
            ),
            ("lark-cli", "event", "schema", "im.message.receive_v1"): result(
                0,
                "Required Scopes:\n  - im:message.p2p_msg:readonly\n",
            ),
            ("lark-cli", "event", "status"): result(0, "Bus: not running"),
        }
    )

    report = check_feishu_readiness(runner=runner)

    assert report["ok"] is False
    assert report["capabilities"]["user_send_message"]["ok"] is False
    assert 'im:message.send_as_user' in report["capabilities"]["user_send_message"]["action"]


def test_check_feishu_readiness_surfaces_cli_failure():
    runner = FakeRunner(
        {
            ("lark-cli", "doctor"): result(1, "", "command not found"),
            ("lark-cli", "auth", "status"): result(1, "", "no auth"),
            ("lark-cli", "event", "schema", "im.message.receive_v1"): result(1, "", "no schema"),
            ("lark-cli", "event", "status"): result(1, "", "no bus"),
        }
    )

    report = check_feishu_readiness(runner=runner)

    assert report["ok"] is False
    assert report["checks"]["doctor"]["ok"] is False
    assert report["checks"]["doctor"]["error"] == "command not found"


def test_check_feishu_readiness_rejects_old_lark_cli_version():
    runner = FakeRunner(
        {
            ("lark-cli", "doctor"): result(0, json.dumps({"ok": True, "cli_version": "1.0.11"})),
            ("lark-cli", "auth", "status"): result(
                0,
                json.dumps({"tokenStatus": "valid", "scope": "im:message.send_as_user"}),
            ),
            ("lark-cli", "event", "schema", "im.message.receive_v1"): result(
                0,
                "Required Scopes:\n  - im:message.p2p_msg:readonly\n",
            ),
            ("lark-cli", "event", "status"): result(0, "Bus: not running"),
        }
    )

    report = check_feishu_readiness(runner=runner)

    assert report["ok"] is False
    assert report["capabilities"]["lark_cli_version"]["ok"] is False
    assert ">= 1.0.23" in report["capabilities"]["lark_cli_version"]["action"]


def test_check_feishu_readiness_reads_cli_version_from_doctor_checks():
    runner = FakeRunner(
        {
            ("lark-cli", "doctor"): result(
                0,
                json.dumps(
                    {
                        "ok": True,
                        "checks": [
                            {"name": "cli_version", "status": "pass", "message": "1.0.11"},
                        ],
                    }
                ),
            ),
            ("lark-cli", "auth", "status"): result(
                0,
                json.dumps({"tokenStatus": "valid", "scope": "im:message.send_as_user"}),
            ),
            ("lark-cli", "event", "schema", "im.message.receive_v1"): result(
                0,
                "Required Scopes:\n  - im:message.p2p_msg:readonly\n",
            ),
            ("lark-cli", "event", "status"): result(0, "Bus: not running"),
        }
    )

    report = check_feishu_readiness(runner=runner)

    assert report["ok"] is False
    assert report["capabilities"]["lark_cli_version"]["ok"] is False


def test_check_feishu_readiness_accepts_profile_argument():
    runner = FakeRunner(
        {
            ("lark-cli", "--profile", "<lark-profile>", "doctor"): result(0, json.dumps({"ok": True, "cli_version": "1.0.23"})),
            ("lark-cli", "--profile", "<lark-profile>", "auth", "status"): result(
                0,
                json.dumps({"tokenStatus": "valid", "scope": "im:message.send_as_user im:chat:create_by_user"}),
            ),
            ("lark-cli", "--profile", "<lark-profile>", "event", "schema", "im.message.receive_v1"): result(
                0,
                "Required Scopes:\n  - im:message.p2p_msg:readonly\n",
            ),
            ("lark-cli", "--profile", "<lark-profile>", "event", "status"): result(0, "Bus: not running"),
        }
    )

    report = check_feishu_readiness(runner=runner, profile="<lark-profile>")

    assert report["ok"] is True
    assert runner.commands[0][:3] == ["lark-cli", "--profile", "<lark-profile>"]
