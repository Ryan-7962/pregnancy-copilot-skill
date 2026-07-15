import zipfile

import pytest

from scripts.create_upgrade_backup import create_backup_from_args
from scripts.init_data_dir import initialize_data_dir
from pregnancy_copilot.backup import (
    create_upgrade_backup,
    render_migration_report,
    restore_upgrade_backup,
    verify_upgrade_backup,
)


def test_create_upgrade_backup_contains_memory_and_events(tmp_path):
    initialize_data_dir(tmp_path)
    (tmp_path / "events" / "events.jsonl").write_text(
        '{"schema_version":"0.1","event_id":"event-001"}\n',
        encoding="utf-8",
    )

    backup_path = create_upgrade_backup(tmp_path, target_version="v0.2", date="2026-05-05")

    assert backup_path == tmp_path / "backups" / "2026-05-05-before-v0.2.zip"
    with zipfile.ZipFile(backup_path) as archive:
        names = set(archive.namelist())
    assert "events/events.jsonl" in names
    assert "memory/profile.yaml" in names
    assert not any(name.startswith("backups/") for name in names)


def test_render_migration_report_mentions_backup_and_counts():
    report = render_migration_report(
        from_version="v0.1",
        to_version="v0.2",
        date="2026-05-05",
        backup_path="pregnancy-data/backups/2026-05-05-before-v0.2.zip",
        events_read=2,
        events_migrated=2,
        manual_review_required=1,
    )

    assert "From: v0.1" in report
    assert "Events read: 2" in report
    assert "Manual review required: 1" in report
    assert "pregnancy-data/backups/2026-05-05-before-v0.2.zip" in report


def test_create_backup_from_args_uses_explicit_date(tmp_path):
    initialize_data_dir(tmp_path)

    backup_path = create_backup_from_args(tmp_path, target_version="v0.2", date="2026-05-05")

    assert backup_path == tmp_path / "backups" / "2026-05-05-before-v0.2.zip"
    assert backup_path.exists()


def test_upgrade_backup_round_trip_restores_exact_user_data(tmp_path):
    source = tmp_path / "pregnancy-data"
    initialize_data_dir(source)
    (source / "events" / "events.jsonl").write_text('{"schema_version":"0.1","event_id":"evt-1"}\n', encoding="utf-8")
    (source / "memory" / "profile.yaml").write_text("schema_version: '0.1'\ndisplay_name: 测试用户\n", encoding="utf-8")
    backup = create_upgrade_backup(source, target_version="v0.2.1", date="2026-07-15")

    verification = verify_upgrade_backup(backup)
    restored = restore_upgrade_backup(backup, tmp_path / "restored")

    assert verification["ok"] is True
    assert verification["encrypted"] is False
    assert (restored / "events" / "events.jsonl").read_bytes() == (source / "events" / "events.jsonl").read_bytes()
    assert (restored / "memory" / "profile.yaml").read_bytes() == (source / "memory" / "profile.yaml").read_bytes()


def test_restore_rejects_zip_path_traversal(tmp_path):
    archive_path = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("../../escaped.txt", "no")

    with pytest.raises(ValueError, match="Unsafe backup member"):
        restore_upgrade_backup(archive_path, tmp_path / "restored")


def test_repeated_same_day_backup_does_not_overwrite_previous_snapshot(tmp_path):
    initialize_data_dir(tmp_path)
    first = create_upgrade_backup(tmp_path, target_version="v0.2.1", date="2026-07-15")
    (tmp_path / "events" / "events.jsonl").write_text("changed\n", encoding="utf-8")
    second = create_upgrade_backup(tmp_path, target_version="v0.2.1", date="2026-07-15")

    assert first.name == "2026-07-15-before-v0.2.1.zip"
    assert second.name == "2026-07-15-before-v0.2.1-2.zip"
    assert first.read_bytes() != second.read_bytes()
