from __future__ import annotations

from pathlib import Path
from typing import Any

from .backup import create_upgrade_backup, verify_upgrade_backup
from .daily_consolidation import consolidate_day
from .data_init import initialize_data_dir
from .onboarding_state import advance_onboarding_state
from .prenatal_plan import sync_profile_next_checkup
from .profile_readiness import check_profile_readiness
from .storage import PregnancyDataStore, atomic_write_text, safe_iso_date


def migrate_to_v030(data_root: str | Path, date: str) -> dict[str, Any]:
    root = Path(data_root)
    migration_date = safe_iso_date(date)
    backup_path = create_upgrade_backup(root, target_version="v0.3.0", date=migration_date)
    backup_verification = verify_upgrade_backup(backup_path)

    initialize_data_dir(root)
    store = PregnancyDataStore(root)
    readiness = check_profile_readiness(root)
    profile_ready = readiness.get("status") == "ready"
    advance_onboarding_state(
        store,
        profile_ready=profile_ready,
        pregnancy_mode="active" if profile_ready else "pending",
        increment_interaction=False,
    )
    synced_plan_item = sync_profile_next_checkup(
        store,
        source_event_id="migration-v0.3.0",
        updated_at=f"{migration_date}T12:00:00+08:00",
    )
    consolidation = consolidate_day(store, migration_date)
    report_path = write_migration_report(
        root,
        migration_date,
        backup_path,
        backup_verification,
        profile_ready,
        synced_plan_item,
        consolidation.index_path,
    )
    return {
        "ok": True,
        "from_version": "v0.2.1",
        "to_version": "v0.3.0",
        "backup_path": backup_path,
        "backup_verification": backup_verification,
        "profile_ready": profile_ready,
        "synced_plan_item": synced_plan_item,
        "daily_index_path": consolidation.index_path,
        "report_path": report_path,
    }


def write_migration_report(
    root: Path,
    date: str,
    backup_path: Path,
    verification: dict[str, Any],
    profile_ready: bool,
    synced_plan_item: dict[str, Any] | None,
    daily_index_path: Path,
) -> Path:
    report_path = root / "reports" / "migrations" / f"{date}-v0.2.1-to-v0.3.0.md"
    content = "\n".join(
        [
            "# Migration Report: v0.2.1 -> v0.3.0",
            "",
            f"- Date: {date}",
            f"- Backup: {backup_path}",
            f"- Backup members verified: {verification['member_count']}",
            f"- Profile ready: {str(profile_ready).lower()}",
            f"- Next checkup synced: {str(bool(synced_plan_item)).lower()}",
            f"- Daily index: {daily_index_path}",
            "",
            "## Data handling",
            "",
            "- Append-only inbox and event history were not rewritten.",
            "- New onboarding, daily-index, and prenatal-plan files were initialized when missing.",
            "- Current context and other derived memory files were rebuilt from local sources.",
            "",
            "## Privacy",
            "",
            "- The backup remains local under pregnancy-data/backups/.",
            "- Backup ZIP files are not encrypted by this Skill; use disk encryption and access controls.",
        ]
    )
    atomic_write_text(report_path, content + "\n")
    return report_path
