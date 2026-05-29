import json

from scripts.init_data_dir import initialize_data_dir
from pregnancy_copilot.adapters.feishu_mock import MockFeishuAdapter
from pregnancy_copilot.event_processor import process_event_stream, process_feishu_event
from pregnancy_copilot.models import TriageResult
from pregnancy_copilot.storage import PregnancyDataStore


def test_process_feishu_event_persists_message_event_context_and_reply(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    adapter = MockFeishuAdapter()

    result = process_feishu_event(
        {
            "event_id": "evt-001",
            "message_id": "om_001",
            "timestamp": "1777777777000",
            "sender_id": "ou_pregnant",
            "chat_id": "oc_chat",
            "chat_type": "p2p",
            "content": "今天肚子有点紧，休息后好了，没有流血也没有流水",
            "message_type": "text",
        },
        store=store,
        adapter=adapter,
    )

    assert result["risk_level"] == "green"
    assert (tmp_path / "inbox" / "raw_feishu_messages").exists()
    events = (tmp_path / "events" / "events.jsonl").read_text(encoding="utf-8")
    assert '"event_id": "evt-001"' in events
    assert '"risk_level": "green"' in events
    context = (tmp_path / "memory" / "current_context.md").read_text(encoding="utf-8")
    assert "今天肚子有点紧" in context
    daily_log = (tmp_path / "daily_logs" / f"{result['timestamp'][:10]}.md").read_text(encoding="utf-8")
    assert "今天肚子有点紧" in daily_log
    assert "green: 1" in daily_log
    assert adapter.sent_replies
    assert "绿色" in adapter.sent_replies[-1][1]


def test_process_feishu_event_red_flag_reply_recommends_doctor_contact(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    adapter = MockFeishuAdapter()

    result = process_feishu_event(
        {
            "event_id": "evt-red",
            "message_id": "om_red",
            "timestamp": "1777777777000",
            "sender_id": "ou_pregnant",
            "content": "我流血了",
        },
        store=store,
        adapter=adapter,
    )

    assert result["risk_level"] == "red"
    assert "红色" in adapter.sent_replies[-1][1]
    assert "联系产科医生" in adapter.sent_replies[-1][1]


def test_process_feishu_event_records_route_and_privacy_override(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    adapter = MockFeishuAdapter()

    result = process_feishu_event(
        {
            "event_id": "evt-route",
            "message_id": "om_route",
            "timestamp": "1777777777000",
            "sender_id": "ou_pregnant",
            "content": "#只同步建议 今天肚子有点紧，休息后好了",
        },
        store=store,
        adapter=adapter,
    )

    assert result["mode"] == "pregnancy_qa"
    assert result["command"] == "#只同步建议"
    assert result["privacy_level"] == "advice_only"
    assert result["user_message_summary"] == "今天肚子有点紧，休息后好了"


def test_process_feishu_event_records_pregnancy_log_without_triage_reply(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    adapter = MockFeishuAdapter()

    result = process_feishu_event(
        {
            "event_id": "evt-log",
            "message_id": "om_log",
            "timestamp": "2026-05-07T13:45:00+08:00",
            "sender_id": "ou_pregnant",
            "content": "今天体重 65kg，早餐吃了鸡蛋和牛奶",
        },
        store=store,
        adapter=adapter,
    )

    assert result["intent"] == "pregnancy_log"
    assert result["event_type"] == "pregnancy_log"
    assert result["triage_required"] is False
    assert result["risk_level"] == "not_applicable"
    assert "风险分级" not in adapter.sent_replies[-1][1]
    assert "已记录" in adapter.sent_replies[-1][1]


def test_process_feishu_event_handles_dad_diary_command(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    adapter = MockFeishuAdapter()

    result = process_feishu_event(
        {
            "event_id": "evt-dad",
            "message_id": "om_dad",
            "timestamp": "1777777777000",
            "sender_id": "ou_partner",
            "sender_role": "partner",
            "content": "#爸爸日记 今天陪她去产检，她有点紧张，我负责整理问题。",
        },
        store=store,
        adapter=adapter,
    )

    assert result["event_type"] == "dad_diary"
    assert result["mode"] == "dad_diary"
    raw_dad_diary = next((tmp_path / "inbox" / "raw_dad_diary").glob("*.md"))
    assert "今天陪她去产检" in raw_dad_diary.read_text(encoding="utf-8")
    diary = next((tmp_path / "baby_diaries").glob("dad-diary-*.md"))
    assert "## 爸爸原文" in diary.read_text(encoding="utf-8")
    assert "爸爸日记已记录" in adapter.sent_replies[-1][1]


def test_process_feishu_event_handles_doctor_question_command(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    adapter = MockFeishuAdapter()

    result = process_feishu_event(
        {
            "event_id": "evt-doctor-question",
            "message_id": "om_doctor_question",
            "timestamp": "1777777777000",
            "sender_id": "ou_pregnant",
            "content": "#产检问题 下次产检要不要问宫颈长度？",
        },
        store=store,
        adapter=adapter,
    )

    assert result["event_type"] == "doctor_question"
    assert result["mode"] == "doctor_questions"
    questions = (tmp_path / "doctor_questions" / "questions.jsonl").read_text(encoding="utf-8")
    assert "下次产检要不要问宫颈长度" in questions
    context = (tmp_path / "memory" / "current_context.md").read_text(encoding="utf-8")
    assert "下次产检要不要问宫颈长度" in context
    assert "已加入下次产检待问问题清单" in adapter.sent_replies[-1][1]


def test_process_feishu_event_handles_baby_diary_command(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    adapter = MockFeishuAdapter()
    store.append_event(
        {
            "schema_version": "0.1",
            "event_id": "evt-week-context",
            "event_type": "dad_diary",
            "timestamp": "2026-05-05T20:00:00+08:00",
            "gestational_age": "20w0d",
            "user_message_summary": "爸爸说这周会认真陪伴",
            "risk_level": "green",
            "privacy_level": "summary",
        }
    )

    result = process_feishu_event(
        {
            "event_id": "evt-baby-diary",
            "message_id": "om_baby_diary",
            "timestamp": "2026-05-06T10:00:00+08:00",
            "sender_id": "ou_pregnant",
            "content": "#宝宝日记",
        },
        store=store,
        adapter=adapter,
    )

    assert result["event_type"] == "baby_diary"
    weekly_review = tmp_path / "weekly_reviews" / "2026-05-04_to_2026-05-10.md"
    baby_diary = tmp_path / "baby_diaries" / "week-2026-05-04_to_2026-05-10.md"
    assert weekly_review.exists()
    assert baby_diary.exists()
    assert "爸爸说这周会认真陪伴" in baby_diary.read_text(encoding="utf-8")
    assert "宝宝周记已生成" in adapter.sent_replies[-1][1]


def test_process_feishu_event_accepts_semantic_triage_advisor(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    adapter = MockFeishuAdapter()

    class SemanticAdvisor:
        def assess(self, text, rule_result):
            return TriageResult(
                risk_level="red",
                reason="语义判断可能存在紧急风险。",
                red_flags_detected=["语义红旗"],
                recommended_action="尽快联系产科医生或急诊。",
                must_include_medical_disclaimer=True,
                must_recommend_doctor_contact=True,
            )

    result = process_feishu_event(
        {
            "event_id": "evt-semantic",
            "message_id": "om_semantic",
            "timestamp": "2026-05-05T09:00:00+08:00",
            "sender_id": "ou_pregnant",
            "content": "下面突然湿了一大片，不确定是不是漏尿",
        },
        store=store,
        adapter=adapter,
        triage_advisor=SemanticAdvisor(),
    )

    assert result["risk_level"] == "red"
    assert "语义红旗" in result["red_flags_detected"]
    assert "红色" in adapter.sent_replies[-1][1]


def test_process_feishu_event_uses_response_provider_for_non_diary_reply(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    adapter = MockFeishuAdapter()

    class ResponseProvider:
        def __init__(self):
            self.prompts = []

        def generate(self, prompt):
            self.prompts.append(prompt)
            return "这是结合上下文生成的更完整回答。"

    provider = ResponseProvider()
    result = process_feishu_event(
        {
            "event_id": "evt-response",
            "message_id": "om_response",
            "timestamp": "2026-05-05T09:00:00+08:00",
            "sender_id": "ou_pregnant",
            "content": "今天肚子有点紧，休息后好了",
        },
        store=store,
        adapter=adapter,
        response_provider=provider,
    )

    assert result["risk_level"] == "green"
    assert adapter.sent_replies[-1][1] == "这是结合上下文生成的更完整回答。"
    assert "今天肚子有点紧" in provider.prompts[0]
    assert "Current Context" in provider.prompts[0]


def test_process_feishu_event_keeps_red_warning_when_response_provider_is_used(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    adapter = MockFeishuAdapter()

    class ResponseProvider:
        def generate(self, prompt):
            return "先深呼吸，观察一下。"

    process_feishu_event(
        {
            "event_id": "evt-red-response",
            "message_id": "om_red_response",
            "timestamp": "2026-05-05T09:00:00+08:00",
            "sender_id": "ou_pregnant",
            "content": "我流血了",
        },
        store=store,
        adapter=adapter,
        response_provider=ResponseProvider(),
    )

    reply = adapter.sent_replies[-1][1]
    assert "先深呼吸" in reply
    assert "尽快联系产科医生" in reply


def test_process_event_stream_reads_ndjson_lines(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    adapter = MockFeishuAdapter()

    count = process_event_stream(
        [
            "\n",
            json.dumps({"event_id": "evt-001", "message_id": "om_001", "content": "这个 B 超数据是什么意思"}),
            "not-json",
        ],
        store=store,
        adapter=adapter,
    )

    assert count == 1
    assert adapter.sent_replies
