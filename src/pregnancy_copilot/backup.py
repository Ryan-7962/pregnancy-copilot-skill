from __future__ import annotations

from pathlib import Path
import shutil
from zipfile import ZIP_DEFLATED, ZipFile

from .storage import safe_iso_date, safe_path_component


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
    "identities",
]


def create_upgrade_backup(data_root: str | Path, target_version: str, date: str) -> Path:
    root = Path(data_root)
    safe_version = safe_path_component(target_version, "target_version")
    safe_date = safe_iso_date(date)
    backup_dir = root / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = unique_backup_path(backup_dir, f"{safe_date}-before-{safe_version}")

    with ZipFile(backup_path, "w", compression=ZIP_DEFLATED) as archive:
        for dirname in BACKUP_DIRS:
            directory = root / dirname
            if not directory.exists():
                continue
            for path in directory.rglob("*"):
                if path.is_file() and "backups" not in path.relative_to(root).parts and ".locks" not in path.parts:
                    archive.write(path, path.relative_to(root).as_posix())
        registry = root / "identity_bindings.yaml"
        if registry.exists():
            archive.write(registry, registry.name)

    return backup_path


def unique_backup_path(backup_dir: Path, stem: str) -> Path:
    candidate = backup_dir / f"{stem}.zip"
    suffix = 2
    while candidate.exists():
        candidate = backup_dir / f"{stem}-{suffix}.zip"
        suffix += 1
    return candidate


def verify_upgrade_backup(backup_path: str | Path) -> dict:
    path = Path(backup_path)
    with ZipFile(path) as archive:
        members = archive.infolist()
        for member in members:
            validate_backup_member(member.filename)
        bad_member = archive.testzip()
        if bad_member:
            raise ValueError(f"Corrupt backup member: {bad_member}")
        return {
            "ok": True,
            "member_count": len(members),
            "encrypted": any(bool(member.flag_bits & 0x1) for member in members),
        }


def restore_upgrade_backup(backup_path: str | Path, target_root: str | Path) -> Path:
    target = Path(target_root)
    if target.exists() and any(target.iterdir()):
        raise ValueError(f"Restore target must be empty: {target}")
    verification = verify_upgrade_backup(backup_path)
    if not verification["ok"]:
        raise ValueError("Backup verification failed.")
    target.mkdir(parents=True, exist_ok=True)
    with ZipFile(backup_path) as archive:
        for member in archive.infolist():
            validate_backup_member(member.filename)
            destination = target / member.filename
            if member.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, destination.open("wb") as output:
                shutil.copyfileobj(source, output)
    return target


def validate_backup_member(name: str) -> None:
    member = Path(name)
    if member.is_absolute() or ".." in member.parts or not member.parts:
        raise ValueError(f"Unsafe backup member: {name!r}")


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
