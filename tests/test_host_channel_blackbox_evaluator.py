import json

from scripts.evaluate_host_channel_blackbox import evaluate_host_channel_blackbox


def test_evaluate_host_channel_blackbox_detects_pass_and_report_write_claim(tmp_path):
    cases_path = tmp_path / "cases.json"
    messages_path = tmp_path / "messages.json"
    cases_path.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "id": "PCSKILL-R01-GREEN",
                        "category": "green",
                        "expect": {
                            "must_contain_any": ["绿色"],
                            "must_contain_all": ["休息"],
                            "must_not_contain_any": ["已录入"],
                        },
                    },
                    {
                        "id": "PCSKILL-R03-REPORT",
                        "category": "report",
                        "expect": {
                            "must_contain_all": ["31mm"],
                            "must_contain_any": ["待记录"],
                            "must_not_contain_any": ["已录入"],
                        },
                    },
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    messages_path.write_text(
        json.dumps(
            {
                "data": {
                    "messages": [
                        {
                            "content": "PCSKILL-R03-REPORT | B 超数据已录入，宫颈 31mm",
                            "sender": {"sender_type": "app"},
                        },
                        {
                            "content": "[PCSKILL-R03-REPORT] 今天 B 超复查：宫颈管长度 31mm",
                            "sender": {"sender_type": "user"},
                        },
                        {
                            "content": "PCSKILL-R01-GREEN | 绿色，休息后缓解",
                            "sender": {"sender_type": "app"},
                        },
                        {
                            "content": "[PCSKILL-R01-GREEN] 今天肚子发紧",
                            "sender": {"sender_type": "user"},
                        },
                    ]
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = evaluate_host_channel_blackbox(cases_path, messages_path)

    assert result["ok"] is False
    by_id = {item["id"]: item for item in result["results"]}
    assert by_id["PCSKILL-R01-GREEN"]["ok"] is True
    assert by_id["PCSKILL-R03-REPORT"]["ok"] is False
    assert by_id["PCSKILL-R03-REPORT"]["checks"]["must_not_contain_any"] is False


def test_evaluate_host_channel_blackbox_allows_write_claim_after_tool_success(tmp_path):
    cases_path = tmp_path / "cases.json"
    messages_path = tmp_path / "messages.json"
    cases_path.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "id": "PCSKILL-R03-REPORT",
                        "category": "report",
                        "expect": {
                            "must_contain_all": ["31mm"],
                            "must_contain_any": ["待记录", "写入成功"],
                            "must_not_contain_any": ["已写入"],
                            "allow_forbidden_if_contains_any": ["record_medical_observation", "写入成功"],
                        },
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    messages_path.write_text(
        json.dumps(
            {
                "data": {
                    "messages": [
                        {
                            "content": "record_medical_observation 三条均写入成功。当前医学状态已写入 31mm。",
                            "sender": {"sender_type": "app"},
                        },
                        {
                            "content": "[PCSKILL-R03-REPORT] 今天 B 超复查：宫颈管长度 31mm",
                            "sender": {"sender_type": "user"},
                        },
                    ]
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = evaluate_host_channel_blackbox(cases_path, messages_path)

    assert result["ok"] is True


def test_evaluate_host_channel_blackbox_allows_write_claim_after_prior_bounded_success_message(tmp_path):
    cases_path = tmp_path / "cases.json"
    messages_path = tmp_path / "messages.json"
    cases_path.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "id": "PCSKILL-R03-REPORT",
                        "category": "report",
                        "expect": {
                            "must_contain_all": ["31mm"],
                            "must_contain_any": ["当前"],
                            "must_not_contain_any": ["已写入"],
                            "allow_forbidden_if_contains_any": ["写入成功"],
                        },
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    messages_path.write_text(
        json.dumps(
            {
                "data": {
                    "messages": [
                        {
                            "content": "PCSKILL-R03-REPORT | 当前医学状态已写入 31mm。",
                            "sender": {"sender_type": "app"},
                        },
                        {
                            "content": "三条观测数据全部写入成功。读回当前状态确认。",
                            "sender": {"sender_type": "app"},
                        },
                        {
                            "content": "[PCSKILL-R03-REPORT] 今天 B 超复查：宫颈管长度 31mm",
                            "sender": {"sender_type": "user"},
                        },
                    ]
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = evaluate_host_channel_blackbox(cases_path, messages_path)

    assert result["ok"] is True


def test_evaluate_host_channel_blackbox_skips_host_diagnostic_noise(tmp_path):
    cases_path = tmp_path / "cases.json"
    messages_path = tmp_path / "messages.json"
    cases_path.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "id": "PCSKILL-R03-REPORT",
                        "category": "report",
                        "expect": {
                            "must_contain_all": ["31mm"],
                            "must_contain_any": ["待记录"],
                            "must_not_contain_any": ["已录入"],
                        },
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    messages_path.write_text(
        json.dumps(
            {
                "data": {
                    "messages": [
                        {
                            "content": "PCSKILL-R03-REPORT | 31mm 是待记录的新数据",
                            "sender": {"sender_type": "app"},
                        },
                        {
                            "content": "宿主调用结果：intent=report_review",
                            "sender": {"sender_type": "app"},
                        },
                        {
                            "content": "[PCSKILL-R03-REPORT] 今天 B 超复查：宫颈管长度 31mm",
                            "sender": {"sender_type": "user"},
                        },
                    ]
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = evaluate_host_channel_blackbox(cases_path, messages_path)

    assert result["ok"] is True
    assert result["results"][0]["reply_excerpt"].startswith("PCSKILL-R03-REPORT")


def test_evaluate_host_channel_blackbox_does_not_cross_next_user_message_boundary(tmp_path):
    cases_path = tmp_path / "cases.json"
    messages_path = tmp_path / "messages.json"
    cases_path.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "id": "PCSKILL-R01-GREEN",
                        "expect": {
                            "must_contain_all": ["绿色"],
                            "must_contain_any": [],
                            "must_not_contain_any": ["红色"],
                        },
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    messages_path.write_text(
        json.dumps(
            {
                "data": {
                    "messages": [
                        {
                            "content": "PCSKILL-R02-RED | 红色，需要就医",
                            "sender": {"sender_type": "app"},
                        },
                        {
                            "content": "[PCSKILL-R02-RED] 出血腹痛",
                            "sender": {"sender_type": "user"},
                        },
                        {
                            "content": "PCSKILL-R01-GREEN | 绿色，休息后缓解",
                            "sender": {"sender_type": "app"},
                        },
                        {
                            "content": "[PCSKILL-R01-GREEN] 肚子发紧",
                            "sender": {"sender_type": "user"},
                        },
                    ]
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = evaluate_host_channel_blackbox(cases_path, messages_path)

    assert result["ok"] is True
    assert "R01" in result["results"][0]["reply_excerpt"]


def test_evaluate_host_channel_blackbox_allows_no_reply_for_pass_through_case(tmp_path):
    cases_path = tmp_path / "cases.json"
    messages_path = tmp_path / "messages.json"
    cases_path.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "id": "PCSKILL-R08-GENERAL",
                        "expect": {
                            "allow_no_reply": True,
                            "must_contain_all": ["歌"],
                            "must_contain_any": ["晚上"],
                            "must_not_contain_any": ["风险分级"],
                        },
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    messages_path.write_text(
        json.dumps(
            {
                "data": {
                    "messages": [
                        {
                            "content": "[PCSKILL-R08-GENERAL] 推荐一首适合晚上听的歌。",
                            "sender": {"sender_type": "user"},
                        }
                    ]
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = evaluate_host_channel_blackbox(cases_path, messages_path)

    assert result["ok"] is True
    assert result["results"][0]["reply_found"] is False
    assert result["results"][0]["checks"]["allow_no_reply"] is True
