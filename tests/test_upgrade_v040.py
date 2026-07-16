import zipfile

import yaml

from pregnancy_copilot.data_init import initialize_data_dir
from pregnancy_copilot.migration_v040 import migrate_to_v040
from pregnancy_copilot.storage import PregnancyDataStore, SCHEMA_VERSION


def test_v040_migration_backs_up_and_preserves_append_only_histories(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    store.append_event(
        {
            "schema_version": SCHEMA_VERSION,
            "event_id": "before-v040",
            "timestamp": "2026-07-16T09:00:00+08:00",
        }
    )
    (tmp_path / "events" / "medical_observations.jsonl").write_text(
        '{"metric_key":"synthetic","value":"1"}\n', encoding="utf-8"
    )
    events_before = (tmp_path / "events" / "events.jsonl").read_bytes()
    medical_before = (tmp_path / "events" / "medical_observations.jsonl").read_bytes()

    result = migrate_to_v040(tmp_path, date="2026-07-16")

    assert result["ok"] is True
    assert result["backup_verification"]["ok"] is True
    assert (tmp_path / "events" / "events.jsonl").read_bytes() == events_before
    assert (tmp_path / "events" / "medical_observations.jsonl").read_bytes() == medical_before
    assert (tmp_path / "external_sources" / "raw").is_dir()
    assert (tmp_path / "memory" / "external_content_index.md").exists()
    onboarding = yaml.safe_load((tmp_path / "memory" / "onboarding_state.yaml").read_text(encoding="utf-8"))
    assert "external_content_audit" in onboarding["pending_topics"]
    assert onboarding["preferences"]["xhs_video_transcription"] == "ask"
    with zipfile.ZipFile(result["backup_path"]) as archive:
        assert archive.read("events/events.jsonl") == events_before
        assert archive.read("events/medical_observations.jsonl") == medical_before
