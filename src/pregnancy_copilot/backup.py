from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


BACKUP_DIRS = [
    "inbox",
    "events",
    "memory",
    "reports",
    "daily_logs",
    "weekly_reviews",
    "husband_summaries",
    "baby_diaries",
    "doctor_questions",
    "feishu_docs",
]


def create_upgrade_backup(data_root: str | Path, target_version: str, date: str) -> Path:
    root = Path(data_root)
    backup_dir = root / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"{date}-before-{target_version}.zip"

    with ZipFile(backup_path, "w", compression=ZIP_DEFLATED) as archive:
        for dirname in BACKUP_DIRS:
            directory = root / dirname
            if not directory.exists():
                continue
            for path in directory.rglob("*"):
                if path.is_file():
                    archive.write(path, path.relative_to(root).as_posix())

    return backup_path


def render_migration_report(
    from_version: str,
    to_version: str,
    date: str,
    backup_path: str,
    events_read: int,
    events_migrated: int,
    manual_review_required: int = 0,
) -> str:
    return "\n".join(
        [
            "# Migration Report",
            "",
            f"From: {from_version}",
            f"To: {to_version}",
            f"Date: {date}",
            "",
            "## Summary",
            "",
            f"- Events read: {events_read}",
            f"- Events migrated: {events_migrated}",
            "- Reports read: 0",
            f"- Manual review required: {manual_review_required}",
            "",
            "## Backup",
            "",
            backup_path,
            "",
            "## Warnings",
            "",
            "- 不删除旧数据；需要人工确认的医学事实必须保留原始 source path。",
        ]
    )
