from pregnancy_copilot.data_init import initialize_data_dir
from pregnancy_copilot.prenatal_plan import upsert_plan_item
from pregnancy_copilot.storage import PregnancyDataStore
from scripts.run_due_reminders import run_due_reminders


def test_due_reminder_script_claims_actions_once(tmp_path):
    initialize_data_dir(tmp_path)
    upsert_plan_item(
        PregnancyDataStore(tmp_path),
        {
            "item_id": "next-checkup",
            "title": "下次产检",
            "scheduled_date": "2026-07-20",
            "status": "scheduled",
            "source": "user_reported",
            "reminder": {"enabled": True, "lead_days": 1},
        },
    )

    first = run_due_reminders(tmp_path, "2026-07-19")
    second = run_due_reminders(tmp_path, "2026-07-19")

    assert first["ok"] is True
    assert first["action_count"] == 1
    assert second["action_count"] == 0
    assert first["actions"][0]["target"] == "host_default_channel"
