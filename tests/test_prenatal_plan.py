import yaml

from pregnancy_copilot.data_init import initialize_data_dir
from pregnancy_copilot.onboarding_state import advance_onboarding_state
from pregnancy_copilot.prenatal_plan import (
    build_due_reminder_actions,
    claim_due_reminder_actions,
    read_prenatal_plan,
    sync_profile_next_checkup,
    upsert_plan_item,
)
from pregnancy_copilot.storage import PregnancyDataStore


def test_initialize_data_dir_creates_empty_prenatal_plan(tmp_path):
    initialize_data_dir(tmp_path)

    plan = yaml.safe_load((tmp_path / "memory" / "prenatal_plan.yaml").read_text(encoding="utf-8"))

    assert plan == {"schema_version": "0.1", "items": []}


def test_upsert_preserves_prior_schedule_when_date_changes(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    base = {
        "item_id": "next-checkup",
        "title": "下次产检",
        "scheduled_date": "2026-07-20",
        "status": "scheduled",
        "source": "user_reported",
        "source_event_id": "evt-1",
        "reminder": {"enabled": True, "lead_days": 1},
    }
    upsert_plan_item(store, base, updated_at="2026-07-15T10:00:00+08:00")
    base["scheduled_date"] = "2026-07-22"
    base["source_event_id"] = "evt-2"

    updated = upsert_plan_item(store, base, updated_at="2026-07-16T10:00:00+08:00")

    assert updated["scheduled_date"] == "2026-07-22"
    assert updated["schedule_history"] == [
        {
            "scheduled_date": "2026-07-20",
            "changed_at": "2026-07-16T10:00:00+08:00",
            "source": "user_reported",
            "source_event_id": "evt-1",
        }
    ]
    assert updated["reminder"]["last_sent_for_date"] is None


def test_suggested_item_remains_distinct_from_confirmed_appointment(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)

    item = upsert_plan_item(
        store,
        {
            "item_id": "suggested-ogtt-window",
            "title": "糖耐检查时间窗",
            "scheduled_date": "2026-08-01",
            "status": "suggested",
            "source": "suggested",
            "guideline_source": "example-guideline-reference",
            "reminder": {"enabled": False, "lead_days": 1},
        },
    )

    assert item["status"] == "suggested"
    assert item["source"] == "suggested"
    assert item["guideline_source"] == "example-guideline-reference"


def test_sync_profile_next_checkup_creates_explicit_plan_item(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    profile_path = tmp_path / "memory" / "profile.yaml"
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    profile["next_checkup"] = "2026-07-20"
    profile_path.write_text(yaml.safe_dump(profile, allow_unicode=True, sort_keys=False), encoding="utf-8")

    item = sync_profile_next_checkup(store, source_event_id="profile-update-1")

    assert item["item_id"] == "profile-next-checkup"
    assert item["scheduled_date"] == "2026-07-20"
    assert item["source"] == "user_reported"
    assert item["reminder"]["enabled"] is False


def test_d_minus_one_reminder_contains_previsit_artifacts_and_is_channel_neutral(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    advance_onboarding_state(
        store,
        preference_updates={"prenatal_reminders_enabled": True, "reminder_lead_days": 1},
        increment_interaction=False,
    )
    upsert_plan_item(
        store,
        {
            "item_id": "next-checkup",
            "title": "下次产检",
            "scheduled_date": "2026-07-20",
            "status": "scheduled",
            "source": "user_reported",
            "reminder": {"enabled": True, "lead_days": 1},
        },
    )

    actions = build_due_reminder_actions(store, "2026-07-19")

    assert len(actions) == 1
    action = actions[0]
    assert action["type"] == "send_prenatal_reminder"
    assert action["target"] == "host_default_channel"
    assert "feishu" not in str(action).lower()
    assert action["scheduled_date"] == "2026-07-20"
    assert action["artifacts"]["pre_visit_sop_path"].endswith("pre_visit_2026-07-20.md")
    assert action["artifacts"]["doctor_questions_path"].endswith("doctor_questions/questions.md")


def test_claimed_reminder_is_not_returned_twice(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    upsert_plan_item(
        store,
        {
            "item_id": "next-checkup",
            "title": "下次产检",
            "scheduled_date": "2026-07-20",
            "status": "scheduled",
            "source": "user_reported",
            "reminder": {"enabled": True, "lead_days": 1},
        },
    )

    first = claim_due_reminder_actions(store, "2026-07-19")
    second = claim_due_reminder_actions(store, "2026-07-19")

    assert len(first) == 1
    assert second == []
    item = read_prenatal_plan(store)["items"][0]
    assert item["reminder"]["last_sent_for_date"] == "2026-07-19"


def test_rescheduling_after_claim_creates_new_due_reminder(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    item = {
        "item_id": "next-checkup",
        "title": "下次产检",
        "scheduled_date": "2026-07-20",
        "status": "scheduled",
        "source": "user_reported",
        "reminder": {"enabled": True, "lead_days": 1},
    }
    upsert_plan_item(store, item)
    assert len(claim_due_reminder_actions(store, "2026-07-19")) == 1
    item["scheduled_date"] = "2026-07-22"
    upsert_plan_item(store, item)

    assert len(claim_due_reminder_actions(store, "2026-07-21")) == 1


def test_failed_artifact_generation_does_not_consume_reminder(tmp_path, monkeypatch):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    upsert_plan_item(
        store,
        {
            "item_id": "next-checkup",
            "title": "下次产检",
            "scheduled_date": "2026-07-20",
            "status": "scheduled",
            "source": "user_reported",
            "reminder": {"enabled": True, "lead_days": 1},
        },
    )

    monkeypatch.setattr("pregnancy_copilot.prenatal_plan.generate_pre_visit_sop", lambda *_: (_ for _ in ()).throw(RuntimeError("disk error")))
    try:
        claim_due_reminder_actions(store, "2026-07-19")
    except RuntimeError as exc:
        assert str(exc) == "disk error"
    else:
        raise AssertionError("expected artifact generation failure")

    item = read_prenatal_plan(store)["items"][0]
    assert item["reminder"]["last_sent_for_date"] is None
