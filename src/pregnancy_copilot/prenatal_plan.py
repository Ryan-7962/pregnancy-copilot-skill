from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml

from .doctor_questions import render_doctor_questions_markdown
from .onboarding_state import read_onboarding_state
from .storage import PregnancyDataStore, SCHEMA_VERSION, atomic_write_text
from .visit_sop import generate_pre_visit_sop


VALID_STATUSES = {"suggested", "scheduled", "completed", "cancelled"}
VALID_SOURCES = {"suggested", "user_reported", "clinician_reported", "report_verified"}


def read_prenatal_plan(store: PregnancyDataStore) -> dict[str, Any]:
    path = prenatal_plan_path(store)
    if not path.exists():
        plan = {"schema_version": SCHEMA_VERSION, "items": []}
        atomic_write_text(path, yaml.safe_dump(plan, allow_unicode=True, sort_keys=False))
        return plan
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Unsupported prenatal plan schema version")
    return {"schema_version": SCHEMA_VERSION, "items": list(payload.get("items") or [])}


def upsert_plan_item(
    store: PregnancyDataStore,
    item: dict[str, Any],
    *,
    updated_at: str | None = None,
) -> dict[str, Any]:
    timestamp = updated_at or now_iso()
    incoming = normalize_plan_item(item, timestamp)
    with store.transaction_lock("prenatal-plan"):
        plan = read_prenatal_plan(store)
        existing_index = next(
            (index for index, current in enumerate(plan["items"]) if current.get("item_id") == incoming["item_id"]),
            None,
        )
        if existing_index is None:
            result = incoming
            plan["items"].append(result)
        else:
            existing = deepcopy(plan["items"][existing_index])
            result = merge_plan_item(existing, incoming, timestamp)
            plan["items"][existing_index] = result
        plan["items"] = sorted(plan["items"], key=lambda row: (row.get("scheduled_date", ""), row.get("item_id", "")))
        write_prenatal_plan(store, plan)
        return deepcopy(result)


def sync_profile_next_checkup(
    store: PregnancyDataStore,
    *,
    source_event_id: str | None = None,
    updated_at: str | None = None,
) -> dict[str, Any] | None:
    profile = store.load_profile()
    scheduled_date = profile.get("next_checkup")
    if not scheduled_date:
        return None
    state = read_onboarding_state(store)
    preferences = state.get("preferences") or {}
    return upsert_plan_item(
        store,
        {
            "item_id": "profile-next-checkup",
            "title": "下次产检",
            "scheduled_date": scheduled_date,
            "status": "scheduled",
            "source": "user_reported",
            "source_event_id": source_event_id,
            "reminder": {
                "enabled": bool(preferences.get("prenatal_reminders_enabled", False)),
                "lead_days": int(preferences.get("reminder_lead_days", 1)),
            },
        },
        updated_at=updated_at,
    )


def build_due_reminder_actions(store: PregnancyDataStore, as_of_date: str) -> list[dict[str, Any]]:
    validate_date(as_of_date)
    plan = read_prenatal_plan(store)
    return [build_reminder_action(store, item, as_of_date) for item in due_items(plan, as_of_date)]


def claim_due_reminder_actions(store: PregnancyDataStore, as_of_date: str) -> list[dict[str, Any]]:
    validate_date(as_of_date)
    candidates = due_items(read_prenatal_plan(store), as_of_date)
    prepared_actions = {
        item["item_id"]: build_reminder_action(store, item, as_of_date)
        for item in candidates
    }
    with store.transaction_lock("prenatal-plan"):
        plan = read_prenatal_plan(store)
        claimed = [item for item in due_items(plan, as_of_date) if item["item_id"] in prepared_actions]
        if claimed:
            claimed_ids = {item["item_id"] for item in claimed}
            for item in plan["items"]:
                if item.get("item_id") in claimed_ids:
                    item.setdefault("reminder", {})["last_sent_for_date"] = as_of_date
            write_prenatal_plan(store, plan)
    return [prepared_actions[item["item_id"]] for item in claimed]


def mark_reminder_sent(store: PregnancyDataStore, item_id: str, sent_for_date: str) -> dict[str, Any]:
    validate_date(sent_for_date)
    with store.transaction_lock("prenatal-plan"):
        plan = read_prenatal_plan(store)
        for item in plan["items"]:
            if item.get("item_id") == item_id:
                item.setdefault("reminder", {})["last_sent_for_date"] = sent_for_date
                write_prenatal_plan(store, plan)
                return deepcopy(item)
    raise KeyError(item_id)


def due_items(plan: dict[str, Any], as_of_date: str) -> list[dict[str, Any]]:
    current = date.fromisoformat(as_of_date)
    result = []
    for item in plan.get("items") or []:
        reminder = item.get("reminder") or {}
        if item.get("status") != "scheduled" or not reminder.get("enabled"):
            continue
        lead_days = int(reminder.get("lead_days", 1))
        due_date = date.fromisoformat(item["scheduled_date"]) - timedelta(days=lead_days)
        if due_date != current or reminder.get("last_sent_for_date") == as_of_date:
            continue
        result.append(deepcopy(item))
    return result


def build_reminder_action(store: PregnancyDataStore, item: dict[str, Any], as_of_date: str) -> dict[str, Any]:
    pre_visit_path = generate_pre_visit_sop(store, item["scheduled_date"])
    questions_path = render_doctor_questions_markdown(store)
    return {
        "action_id": f"prenatal-reminder:{item['item_id']}:{as_of_date}",
        "type": "send_prenatal_reminder",
        "target": "host_default_channel",
        "send_reply": True,
        "item_id": item["item_id"],
        "title": item["title"],
        "scheduled_date": item["scheduled_date"],
        "message": (
            f"提醒：{item['title']}安排在 {item['scheduled_date']}。"
            "请检查报告材料和待问医生问题；就诊后可把医生原话发给我整理下一阶段行动 SOP。"
        ),
        "artifacts": {
            "pre_visit_sop_path": pre_visit_path.relative_to(store.root).as_posix(),
            "doctor_questions_path": questions_path.relative_to(store.root).as_posix(),
        },
    }


def normalize_plan_item(item: dict[str, Any], timestamp: str) -> dict[str, Any]:
    payload = deepcopy(item)
    title = str(payload.get("title") or "").strip()
    scheduled_date = str(payload.get("scheduled_date") or "").strip()
    status = str(payload.get("status") or "scheduled")
    source = str(payload.get("source") or "user_reported")
    if not title:
        raise ValueError("Prenatal plan title is required")
    validate_date(scheduled_date)
    if status not in VALID_STATUSES:
        raise ValueError(f"Unsupported prenatal plan status: {status!r}")
    if source not in VALID_SOURCES:
        raise ValueError(f"Unsupported prenatal plan source: {source!r}")
    if status == "suggested" and source != "suggested":
        raise ValueError("Suggested plan items must use source='suggested'")
    if source == "suggested" and not payload.get("guideline_source"):
        raise ValueError("Suggested plan items require guideline_source")
    reminder = dict(payload.get("reminder") or {})
    lead_days = int(reminder.get("lead_days", 1))
    if lead_days < 0 or lead_days > 30:
        raise ValueError("reminder.lead_days must be between 0 and 30")
    item_id = str(payload.get("item_id") or stable_item_id(title, scheduled_date, payload.get("source_event_id")))
    return {
        "item_id": item_id,
        "title": title,
        "scheduled_date": scheduled_date,
        "status": status,
        "source": source,
        "source_event_id": payload.get("source_event_id"),
        "guideline_source": payload.get("guideline_source"),
        "reminder": {
            "enabled": bool(reminder.get("enabled", False)),
            "lead_days": lead_days,
            "last_sent_for_date": reminder.get("last_sent_for_date"),
        },
        "notes": payload.get("notes"),
        "schedule_history": list(payload.get("schedule_history") or []),
        "created_at": payload.get("created_at") or timestamp,
        "updated_at": timestamp,
    }


def merge_plan_item(existing: dict[str, Any], incoming: dict[str, Any], timestamp: str) -> dict[str, Any]:
    history = list(existing.get("schedule_history") or [])
    date_changed = existing.get("scheduled_date") != incoming.get("scheduled_date")
    if date_changed:
        history.append(
            {
                "scheduled_date": existing.get("scheduled_date"),
                "changed_at": timestamp,
                "source": existing.get("source"),
                "source_event_id": existing.get("source_event_id"),
            }
        )
    result = deepcopy(incoming)
    result["created_at"] = existing.get("created_at") or incoming["created_at"]
    result["schedule_history"] = history
    if date_changed:
        result["reminder"]["last_sent_for_date"] = None
    elif incoming["reminder"].get("last_sent_for_date") is None:
        result["reminder"]["last_sent_for_date"] = (existing.get("reminder") or {}).get("last_sent_for_date")
    return result


def prenatal_plan_path(store: PregnancyDataStore) -> Path:
    path = store.root / "memory" / "prenatal_plan.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write_prenatal_plan(store: PregnancyDataStore, plan: dict[str, Any]) -> Path:
    path = prenatal_plan_path(store)
    atomic_write_text(path, yaml.safe_dump(plan, allow_unicode=True, sort_keys=False))
    return path


def stable_item_id(title: str, scheduled_date: str, source_event_id: Any) -> str:
    digest = sha256(f"{title}|{scheduled_date}|{source_event_id or ''}".encode("utf-8")).hexdigest()[:12]
    return f"plan-{digest}"


def validate_date(value: str) -> None:
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Invalid scheduled date: {value!r}") from exc


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()
