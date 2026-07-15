from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .backup import create_upgrade_backup, verify_upgrade_backup
from .context_builder import build_current_context
from .medical_state import rebuild_current_medical_state
from .storage import PregnancyDataStore, atomic_write_text, safe_iso_date


OLD_TEMPLATE_MARKERS = {
    "profile_name": "Example Pregnancy Profile",
    "display_name": "孕妇",
    "baby_nickname": "宝宝",
    "current_gestational_age": "20w0d",
    "hospital.name": "示例医院",
}
OLD_TEMPLATE_FOCUS = ["20 周大排畸", "胎盘位置", "宫颈长度", "睡眠和焦虑"]


def migrate_to_v021(data_root: str | Path, date: str) -> dict[str, Any]:
    root = Path(data_root)
    migration_date = safe_iso_date(date)
    store = PregnancyDataStore(root)
    profile = store.load_profile()

    backup_path = create_upgrade_backup(root, target_version="v0.2.1", date=migration_date)
    backup_verification = verify_upgrade_backup(backup_path)
    manual_review_fields = find_old_template_fields(profile)
    cleared_unedited_template = is_unedited_v020_template(profile)

    if cleared_unedited_template:
        with store.transaction_lock("profile"):
            profile = store.load_profile()
            clear_old_template_values(profile)
            atomic_write_text(
                root / "memory" / "profile.yaml",
                yaml.safe_dump(profile, allow_unicode=True, sort_keys=False),
            )
        manual_review_fields = []

    rebuild_current_medical_state(store)
    build_current_context(store)
    report_path = write_migration_report(
        root,
        migration_date,
        backup_path,
        backup_verification,
        cleared_unedited_template,
        manual_review_fields,
    )
    return {
        "ok": True,
        "from_version": "v0.2.0",
        "to_version": "v0.2.1",
        "backup_path": backup_path,
        "backup_verification": backup_verification,
        "cleared_unedited_template": cleared_unedited_template,
        "manual_review_fields": manual_review_fields,
        "report_path": report_path,
    }


def is_unedited_v020_template(profile: dict[str, Any]) -> bool:
    return all(read_field(profile, field) == value for field, value in OLD_TEMPLATE_MARKERS.items()) and profile.get(
        "current_focus"
    ) == OLD_TEMPLATE_FOCUS


def find_old_template_fields(profile: dict[str, Any]) -> list[str]:
    fields = [field for field, value in OLD_TEMPLATE_MARKERS.items() if read_field(profile, field) == value]
    if profile.get("current_focus") == OLD_TEMPLATE_FOCUS:
        fields.append("current_focus")
    return sorted(fields)


def clear_old_template_values(profile: dict[str, Any]) -> None:
    profile["profile_name"] = None
    profile["display_name"] = None
    profile["baby_nickname"] = None
    profile["current_gestational_age"] = None
    profile["gestational_age_as_of"] = None
    hospital = profile.setdefault("hospital", {})
    hospital["name"] = None
    hospital["city"] = None
    hospital["care_model"] = None
    profile["current_focus"] = []


def read_field(profile: dict[str, Any], field: str) -> Any:
    value: Any = profile
    for part in field.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def write_migration_report(
    root: Path,
    date: str,
    backup_path: Path,
    verification: dict[str, Any],
    cleared_unedited_template: bool,
    manual_review_fields: list[str],
) -> Path:
    report_path = root / "reports" / "migrations" / f"{date}-v0.2.0-to-v0.2.1.md"
    review_text = "无" if not manual_review_fields else "、".join(manual_review_fields)
    content = "\n".join(
        [
            "# Migration Report: v0.2.0 -> v0.2.1",
            "",
            f"- Date: {date}",
            f"- Backup: {backup_path}",
            f"- Backup members verified: {verification['member_count']}",
            f"- Cleared fully unedited v0.2.0 template: {str(cleared_unedited_template).lower()}",
            f"- Manual review fields: {review_text}",
            "",
            "## Privacy",
            "",
            "- 备份位于本地 pregnancy-data/backups/ 内。",
            "- ZIP 默认未加密；请依赖操作系统磁盘加密和访问权限保护。",
            "",
            "## Data handling",
            "",
            "- Append-only inbox, events, and medical observations were not deleted.",
            "- Derived current medical state and current context were rebuilt.",
        ]
    )
    atomic_write_text(report_path, content + "\n")
    return report_path
