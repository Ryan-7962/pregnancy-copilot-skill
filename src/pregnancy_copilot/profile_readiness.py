from __future__ import annotations

from pathlib import Path
from typing import Any

from .storage import PregnancyDataStore


TEMPLATE_VALUES = {
    "profile_name": {"Example Pregnancy Profile", "User Pregnancy Profile", ""},
    "display_name": {"孕妇", ""},
    "baby_nickname": {"宝宝", ""},
    "current_gestational_age": {"20w0d", "20w0d", ""},
    "hospital.name": {"示例医院", "Example Hospital", ""},
}


def check_profile_readiness(data_root: str | Path) -> dict[str, Any]:
    store = PregnancyDataStore(data_root)
    profile = store.load_profile()
    checks = {
        "identity": check_identity(profile),
        "pregnancy_anchor": check_pregnancy_anchor(profile),
        "hospital": check_hospital(profile),
        "preferences": check_preferences(profile),
        "privacy_defaults": check_privacy_defaults(profile),
    }
    missing_or_template_fields = sorted(
        {
            field
            for check in checks.values()
            for field in check["missing_or_template_fields"]
        }
    )
    return {
        "ok": not missing_or_template_fields,
        "status": "ready" if not missing_or_template_fields else "needs_review",
        "missing_or_template_fields": missing_or_template_fields,
        "checks": checks,
        "next_steps": build_next_steps(missing_or_template_fields),
    }


def check_identity(profile: dict[str, Any]) -> dict[str, Any]:
    return check_fields(
        profile,
        [
            ("profile_name", profile.get("profile_name")),
            ("display_name", profile.get("display_name")),
            ("baby_nickname", profile.get("baby_nickname")),
            ("timezone", profile.get("timezone")),
        ],
    )


def check_pregnancy_anchor(profile: dict[str, Any]) -> dict[str, Any]:
    gestational_age = profile.get("current_gestational_age")
    due_date = profile.get("due_date")
    missing = []
    if is_template_or_empty("current_gestational_age", gestational_age) and not due_date:
        missing.append("current_gestational_age")
    return {
        "ok": not missing,
        "missing_or_template_fields": missing,
        "summary": "Set current_gestational_age or due_date so the host can anchor pregnancy timing.",
    }


def check_hospital(profile: dict[str, Any]) -> dict[str, Any]:
    hospital = profile.get("hospital") or {}
    return check_fields(
        profile,
        [
            ("hospital.name", hospital.get("name")),
            ("hospital.city", hospital.get("city")),
            ("hospital.care_model", hospital.get("care_model")),
        ],
    )


def check_preferences(profile: dict[str, Any]) -> dict[str, Any]:
    preferences = profile.get("preferences") or {}
    return check_fields(
        profile,
        [
            ("preferences.language", preferences.get("language")),
            ("preferences.tone", preferences.get("tone")),
            ("preferences.medical_disclaimer_level", preferences.get("medical_disclaimer_level")),
        ],
    )


def check_privacy_defaults(profile: dict[str, Any]) -> dict[str, Any]:
    preferences = profile.get("preferences") or {}
    privacy = profile.get("privacy") or {}
    return check_fields(
        profile,
        [
            ("privacy.default_privacy_level", privacy.get("default_privacy_level")),
            ("privacy.require_confirmation_for_full_share", privacy.get("require_confirmation_for_full_share")),
            ("preferences.partner_share_default", preferences.get("partner_share_default")),
            ("preferences.husband_share_default", preferences.get("husband_share_default")),
        ],
    )


def check_fields(profile: dict[str, Any], fields: list[tuple[str, Any]]) -> dict[str, Any]:
    missing = [field for field, value in fields if is_template_or_empty(field, value)]
    return {
        "ok": not missing,
        "missing_or_template_fields": missing,
        "summary": "Ready" if not missing else "Review required",
    }


def is_template_or_empty(field: str, value: Any) -> bool:
    if value is None or value == "":
        return True
    template_values = TEMPLATE_VALUES.get(field, set())
    return str(value) in template_values


def build_next_steps(fields: list[str]) -> list[str]:
    if not fields:
        return ["Profile is ready for real use."]
    return [f"Edit pregnancy-data/memory/profile.yaml: set a real value for {field}." for field in fields]
