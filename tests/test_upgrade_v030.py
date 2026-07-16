import zipfile

import yaml

from pregnancy_copilot.data_init import initialize_data_dir
from pregnancy_copilot.migration_v030 import migrate_to_v030
from pregnancy_copilot.storage import PregnancyDataStore, SCHEMA_VERSION


def test_v030_migration_backs_up_and_preserves_append_only_history(tmp_path):
    initialize_data_dir(tmp_path)
    (tmp_path / "memory" / "onboarding_state.yaml").unlink()
    (tmp_path / "memory" / "prenatal_plan.yaml").unlink()
    store = PregnancyDataStore(tmp_path)
    store.append_event(
        {
            "schema_version": SCHEMA_VERSION,
            "event_id": "evt-before-upgrade",
            "timestamp": "2026-07-15T10:00:00+08:00",
        }
    )
    events_before = (tmp_path / "events" / "events.jsonl").read_bytes()

    result = migrate_to_v030(tmp_path, date="2026-07-15")

    assert result["ok"] is True
    assert result["backup_verification"]["ok"] is True
    assert (tmp_path / "events" / "events.jsonl").read_bytes() == events_before
    assert (tmp_path / "memory" / "onboarding_state.yaml").exists()
    assert (tmp_path / "memory" / "prenatal_plan.yaml").exists()
    assert (tmp_path / "memory" / "daily_conversation_index.yaml").exists()
    with zipfile.ZipFile(result["backup_path"]) as archive:
        assert archive.read("events/events.jsonl") == events_before
    report = result["report_path"].read_text(encoding="utf-8")
    assert "Append-only inbox and event history were not rewritten" in report


def test_v030_migration_activates_ready_profile_and_syncs_next_checkup(tmp_path):
    initialize_data_dir(tmp_path)
    (tmp_path / "memory" / "onboarding_state.yaml").unlink()
    (tmp_path / "memory" / "prenatal_plan.yaml").unlink()
    profile_path = tmp_path / "memory" / "profile.yaml"
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    profile["last_menstrual_period"] = "2026-05-01"
    profile["next_checkup"] = "2026-07-20"
    profile_path.write_text(yaml.safe_dump(profile, allow_unicode=True, sort_keys=False), encoding="utf-8")

    migrate_to_v030(tmp_path, date="2026-07-15")
    onboarding = yaml.safe_load((tmp_path / "memory" / "onboarding_state.yaml").read_text(encoding="utf-8"))
    plan = yaml.safe_load((tmp_path / "memory" / "prenatal_plan.yaml").read_text(encoding="utf-8"))

    assert onboarding["pregnancy_mode"] == "active"
    assert "minimum_profile" in onboarding["completed_topics"]
    assert plan["items"][0]["scheduled_date"] == "2026-07-20"
