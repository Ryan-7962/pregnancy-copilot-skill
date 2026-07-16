from __future__ import annotations

from pathlib import Path
from typing import Any

from .backup import create_upgrade_backup, verify_upgrade_backup
from .data_init import initialize_data_dir
from .external_content.storage import ExternalContentStore
from .onboarding_state import advance_onboarding_state
from .profile_readiness import check_profile_readiness
from .storage import PregnancyDataStore, atomic_write_text, safe_iso_date


def migrate_to_v040(data_root: str | Path, date: str) -> dict[str, Any]:
    root = Path(data_root)
    migration_date = safe_iso_date(date)
    backup_path = create_upgrade_backup(root, target_version="v0.4.0", date=migration_date)
    backup_verification = verify_upgrade_backup(backup_path)

    initialize_data_dir(root)
    store = PregnancyDataStore(root)
    profile_ready = check_profile_readiness(root).get("status") == "ready"
    onboarding = advance_onboarding_state(
        store,
        profile_ready=profile_ready,
        pregnancy_mode="active" if profile_ready else "pending",
        increment_interaction=False,
    )
    external_index = ExternalContentStore(root).write_compact_index()
    report_path = root / "reports" / "migrations" / f"{migration_date}-v0.3.0-to-v0.4.0.md"
    atomic_write_text(
        report_path,
        "\n".join(
            [
                "# Migration Report: v0.3.0 -> v0.4.0",
                "",
                f"- Date: {migration_date}",
                f"- Backup: {backup_path}",
                f"- Backup members verified: {backup_verification['member_count']}",
                f"- External content index: {external_index}",
                "",
                "## Data handling",
                "",
                "- Append-only inbox, event, and medical-observation histories were not rewritten.",
                "- External-source directories and derived compact index were initialized.",
                "- Xiaohongshu and ASR credentials remain outside pregnancy-data.",
            ]
        )
        + "\n",
    )
    return {
        "ok": True,
        "from_version": "v0.3.0",
        "to_version": "v0.4.0",
        "backup_path": backup_path,
        "backup_verification": backup_verification,
        "onboarding": onboarding,
        "external_index_path": external_index,
        "report_path": report_path,
    }
