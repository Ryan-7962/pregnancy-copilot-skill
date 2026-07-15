from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any


PREGNANCY_DAYS = 280


def calculate_gestational_age(profile: dict[str, Any], as_of: str | date | datetime | None = None) -> str | None:
    target_date = parse_date(as_of) if as_of is not None else date.today()
    lmp = parse_date(profile.get("last_menstrual_period"))
    if lmp:
        return format_gestational_days((target_date - lmp).days)

    due_date = parse_date(profile.get("due_date"))
    if due_date:
        return format_gestational_days(PREGNANCY_DAYS - (due_date - target_date).days)

    static_age = parse_gestational_age(profile.get("current_gestational_age"))
    static_as_of = parse_date(profile.get("gestational_age_as_of"))
    if static_age is not None and static_as_of:
        return format_gestational_days(static_age + (target_date - static_as_of).days)
    return str(profile.get("current_gestational_age") or "") or None


def parse_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def parse_gestational_age(value: Any) -> int | None:
    if not value:
        return None
    match = re.fullmatch(r"(\d{1,2})w(\d)d", str(value), flags=re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1)) * 7 + int(match.group(2))


def format_gestational_days(days: int) -> str | None:
    if days < 0 or days > PREGNANCY_DAYS + 21:
        return None
    return f"{days // 7}w{days % 7}d"
