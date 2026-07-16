from pregnancy_copilot.daily_consolidation import consolidate_day
from pregnancy_copilot.host_runtime import HostMessageRequest, process_host_message
from pregnancy_copilot.prenatal_plan import claim_due_reminder_actions, read_prenatal_plan
from pregnancy_copilot.storage import PregnancyDataStore


def send(root, text: str, minute: int):
    return process_host_message(
        HostMessageRequest(
            text=text,
            sender_id="synthetic-pregnant-user",
            sender_role="pregnant_user",
            conversation_id="synthetic-pregnancy-window",
            channel="synthetic_host",
            timestamp=f"2026-07-15T10:{minute:02d}:00+08:00",
        ),
        root,
    )


def test_v030_end_to_end_answer_memory_calendar_and_reminder(tmp_path):
    first = send(tmp_path, "我刚怀孕，今天有点恶心，能先告诉我怎么观察吗？", 0)
    profile = send(tmp_path, "补充建档：末次月经是 2026-05-01，下次产检：2026-07-20", 1)
    enabled = send(tmp_path, "开启产检提醒，提前 1 天", 2)
    raw_path = tmp_path / "inbox" / "raw_synthetic_host_messages" / "2026-07-15.md"
    raw_before_private = raw_path.read_bytes()
    private = send(tmp_path, "这条不记录：我只想聊点别的", 3)
    consolidation = consolidate_day(PregnancyDataStore(tmp_path), "2026-07-15")
    first_reminders = claim_due_reminder_actions(PregnancyDataStore(tmp_path), "2026-07-19")
    second_reminders = claim_due_reminder_actions(PregnancyDataStore(tmp_path), "2026-07-19")
    plan = read_prenatal_plan(PregnancyDataStore(tmp_path))

    assert first.host_action["answer_first"] is True
    assert first.context_package["tutorial_nudge"]["topic"] == "welcome_and_scope"
    assert profile.context_package["profile_readiness"]["status"] == "ready"
    assert enabled.context_package["onboarding"]["preferences"]["prenatal_reminders_enabled"] is True
    assert private.context_package["memory_write_decision"]["record_mode"] == "no_record"
    assert raw_path.read_bytes() == raw_before_private
    assert consolidation.message_count == 3
    assert consolidation.index_path.exists()
    assert plan["items"][0]["scheduled_date"] == "2026-07-20"
    assert len(first_reminders) == 1
    assert first_reminders[0]["target"] == "host_default_channel"
    assert second_reminders == []
