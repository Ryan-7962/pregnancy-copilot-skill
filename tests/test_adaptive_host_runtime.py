from pregnancy_copilot.host_runtime import HostMessageRequest, process_host_message
from pregnancy_copilot.prenatal_plan import build_due_reminder_actions, read_prenatal_plan
from pregnancy_copilot.storage import PregnancyDataStore
from tests.helpers import make_profile_ready


def request(text: str, timestamp: str = "2026-07-15T10:00:00+08:00") -> HostMessageRequest:
    return HostMessageRequest(
        text=text,
        sender_id="pregnant-user",
        sender_role="pregnant_user",
        conversation_id="pregnancy-window",
        channel="host_agent",
        timestamp=timestamp,
    )


def test_fresh_symptom_question_uses_answer_first_contract_with_one_nudge(tmp_path):
    result = process_host_message(request("今天肚子有点紧，休息后缓解，没有出血和流液"), tmp_path)

    assert result.handled is True
    assert result.host_action["type"] == "answer_with_context_package"
    assert result.host_action["answer_first"] is True
    assert result.context_package["output_contract"]["must_answer_user_question_first"] is True
    assert result.context_package["profile_readiness"]["status"] == "needs_review"
    assert result.context_package["tutorial_nudge"]["topic"] == "welcome_and_scope"
    assert result.context_package["memory_write_decision"]["structured_event"] is True
    assert result.context_package["memory_write_decision"]["medical_fact_update"] is False
    assert "先完成孕期建档，再进入正式问答" not in result.reply_text
    assert result.event["intent"] == "medical_triage"
    assert result.event["gestational_age"] == "unknown"


def test_fresh_general_question_is_answered_with_unknown_context_not_profile_gate(tmp_path):
    result = process_host_message(request("明天天气怎么样，顺便推荐一首歌"), tmp_path)

    assert result.intent == "pregnancy_context"
    assert result.event is None
    assert result.risk_level == "not_applicable"
    assert result.host_action["type"] == "answer_with_context_package"
    assert result.context_package["memory_write_decision"]["raw_message"] is True
    assert result.context_package["memory_write_decision"]["structured_event"] is False
    assert result.context_package["tutorial_nudge"]["topic"] == "welcome_and_scope"


def test_red_flag_bypasses_tutorial_and_keeps_urgent_response(tmp_path):
    result = process_host_message(request("我现在大量出血并且晕倒了"), tmp_path)

    assert result.risk_level == "red"
    assert result.context_package["tutorial_nudge"] is None
    assert "尽快" in result.reply_text or "急诊" in result.reply_text


def test_profile_can_progress_while_user_continues_asking_questions(tmp_path):
    first = process_host_message(request("我刚怀孕，可以喝咖啡吗？"), tmp_path)
    second = process_host_message(
        request("补充建档：末次月经是 2026-05-01。另外每天咖啡因多少比较合适？", "2026-07-15T10:01:00+08:00"),
        tmp_path,
    )

    assert first.context_package["tutorial_nudge"]["topic"] == "welcome_and_scope"
    assert second.context_package["profile_readiness"]["status"] == "ready"
    assert second.host_action["type"] == "answer_with_context_package"
    assert second.context_package["output_contract"]["must_answer_user_question_first"] is True
    assert second.context_package["tutorial_nudge"]["topic"] == "medical_truth"
    assert "已保存" in second.reply_text


def test_skip_tutorial_stops_future_nudges(tmp_path):
    skipped = process_host_message(request("跳过教程，我想直接聊今天的心情"), tmp_path)
    later = process_host_message(request("今天有点累", "2026-07-15T10:01:00+08:00"), tmp_path)

    assert skipped.context_package["tutorial_nudge"] is None
    assert skipped.context_package["onboarding"]["tutorial_status"] == "dismissed"
    assert later.context_package["tutorial_nudge"] is None


def test_no_record_control_suppresses_raw_and_structured_writes(tmp_path):
    result = process_host_message(request("这条不记录：今天有点焦虑，只回答我怎么放松"), tmp_path)

    assert result.context_package["memory_write_decision"] == {
        "record_mode": "no_record",
        "raw_message": False,
        "structured_event": False,
        "medical_fact_update": False,
    }
    assert result.event is None
    assert result.artifacts == {}
    assert not list((tmp_path / "inbox").glob("**/*.md"))
    assert not (tmp_path / "events" / "events.jsonl").exists()


def test_install_action_is_concise_and_truthful(tmp_path):
    from pregnancy_copilot.host_runtime import build_install_onboarding_action

    action = build_install_onboarding_action(tmp_path, "agent_default", "pregnancy-window")

    assert action["type"] == "collect_profile"
    assert action["blocking"] is False
    assert "孕期助手" in action["reply_text"]
    assert "都可以和我聊" in action["reply_text"]
    assert "不是医生" in action["reply_text"]
    assert "宿主模型" in action["reply_text"]
    assert "末次月经" in action["reply_text"]
    assert len(action["reply_text"].splitlines()) <= 10


def test_ready_profile_can_update_next_checkup_during_normal_chat(tmp_path):
    make_profile_ready(tmp_path)

    result = process_host_message(
        request("补充建档：下次产检：2026-07-20", "2026-07-15T10:00:00+08:00"),
        tmp_path,
    )
    plan = read_prenatal_plan(PregnancyDataStore(tmp_path))

    assert result.intent == "profile_onboarding"
    assert plan["items"][0]["item_id"] == "profile-next-checkup"
    assert plan["items"][0]["scheduled_date"] == "2026-07-20"


def test_chat_command_enables_existing_prenatal_reminder(tmp_path):
    make_profile_ready(tmp_path)
    process_host_message(request("补充建档：下次产检：2026-07-20"), tmp_path)

    result = process_host_message(
        request("开启产检提醒，提前 1 天", "2026-07-15T10:01:00+08:00"),
        tmp_path,
    )
    store = PregnancyDataStore(tmp_path)
    item = read_prenatal_plan(store)["items"][0]

    assert result.context_package["onboarding"]["preferences"]["prenatal_reminders_enabled"] is True
    assert item["reminder"]["enabled"] is True
    assert len(build_due_reminder_actions(store, "2026-07-19")) == 1
