from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

import yaml

from .context_builder import contains_emotion_signal, read_events
from .storage import PregnancyDataStore, SCHEMA_VERSION, atomic_write_text


DAILY_METRICS_YAML = "memory/daily_metrics.yaml"
DAILY_METRICS_MD = "memory/daily_metrics.md"
WEIGHT_PATTERN = re.compile(r"(?:体重|晨起体重|早晨体重)[：:\s]*([0-9]+(?:\.[0-9]+)?)\s*(?:kg|KG|公斤)")
BLOOD_PRESSURE_PATTERN = re.compile(
    r"(?:血压|BP)[：:\s]*([0-9]{2,3})\s*[/／]\s*([0-9]{2,3})(?:\s*(?:mmHg|毫米汞柱))?",
    flags=re.IGNORECASE,
)
DIET_KEYWORDS = ["早餐", "午餐", "晚餐", "饮食", "吃了"]
ACTIVITY_KEYWORDS = ["散步", "运动", "骑行", "瑜伽", "步行"]
SLEEP_KEYWORDS = ["睡眠", "睡了", "睡不好", "失眠"]


def build_daily_metrics_index(store: PregnancyDataStore, recent_days: int = 14) -> dict[str, Any]:
    store.ensure_dirs()
    events = [
        event
        for event in read_events(store)
        if event.get("import_status") != "draft" and event.get("privacy_level") != "private"
    ]
    days: dict[str, dict[str, Any]] = {}
    weight_points: list[dict[str, Any]] = []
    blood_pressure_points: list[dict[str, Any]] = []

    for event in events:
        date = str(event.get("timestamp", ""))[:10]
        if len(date) != 10:
            continue
        day = days.setdefault(date, empty_day(date))
        summary = event.get("user_message_summary") or ""
        weight = extract_weight_kg(summary)
        if weight is not None:
            point = {
                "value": weight,
                "unit": "kg",
                "date": date,
                "timestamp": event.get("timestamp"),
                "source_event_id": event.get("event_id"),
            }
            day["weight"] = point
            weight_points.append(point)
        blood_pressure = extract_blood_pressure(summary)
        if blood_pressure is not None:
            point = {
                **blood_pressure,
                "date": date,
                "timestamp": event.get("timestamp"),
                "source_event_id": event.get("event_id"),
            }
            day["blood_pressure_readings"].append(point)
            blood_pressure_points.append(point)
        entry = {"event_id": event.get("event_id"), "summary": summary}
        event_type = event.get("event_type")
        if event_type == "mood_support" or contains_emotion_signal(summary):
            day["mood_entries"].append(entry)
        if contains_any(summary, DIET_KEYWORDS):
            day["diet_entries"].append(entry)
        if contains_any(summary, ACTIVITY_KEYWORDS):
            day["activity_entries"].append(entry)
        if contains_any(summary, SLEEP_KEYWORDS):
            day["sleep_entries"].append(entry)

    trimmed_days = dict(sorted(days.items())[-recent_days:])
    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "principle": "Daily metrics are extracted summaries for quick context. Source events remain the audit trail; do not infer missing daily values.",
        "days": trimmed_days,
        "weight_trend": build_weight_trend(weight_points),
        "blood_pressure_trend": build_blood_pressure_trend(blood_pressure_points),
    }
    write_daily_metrics_yaml(store, payload)
    write_daily_metrics_markdown(store, payload)
    return payload


def empty_day(date: str) -> dict[str, Any]:
    return {
        "date": date,
        "weight": None,
        "blood_pressure_readings": [],
        "mood_entries": [],
        "diet_entries": [],
        "activity_entries": [],
        "sleep_entries": [],
    }


def extract_weight_kg(text: str) -> float | None:
    match = WEIGHT_PATTERN.search(text)
    if not match:
        return None
    value = float(match.group(1))
    return int(value) if value.is_integer() else value


def extract_blood_pressure(text: str) -> dict[str, Any] | None:
    match = BLOOD_PRESSURE_PATTERN.search(text)
    if not match:
        return None
    systolic = int(match.group(1))
    diastolic = int(match.group(2))
    if not 50 <= systolic <= 300 or not 30 <= diastolic <= 200 or systolic <= diastolic:
        return None
    return {"systolic": systolic, "diastolic": diastolic, "unit": "mmHg"}


def build_weight_trend(weight_points: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(weight_points, key=lambda item: (str(item.get("timestamp") or ""), str(item.get("source_event_id") or "")))
    if not ordered:
        return {"latest": None, "previous": None, "delta_kg": None}
    latest = ordered[-1]
    previous = ordered[-2] if len(ordered) > 1 else None
    delta = None
    if previous:
        delta = round(float(latest["value"]) - float(previous["value"]), 2)
    return {"latest": latest, "previous": previous, "delta_kg": delta}


def build_blood_pressure_trend(points: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(points, key=lambda item: (str(item.get("timestamp") or ""), str(item.get("source_event_id") or "")))
    if not ordered:
        return {"latest": None, "previous": None, "delta": None}
    latest = ordered[-1]
    previous = ordered[-2] if len(ordered) > 1 else None
    delta = None
    if previous:
        delta = {
            "systolic": latest["systolic"] - previous["systolic"],
            "diastolic": latest["diastolic"] - previous["diastolic"],
        }
    return {"latest": latest, "previous": previous, "delta": delta}


def write_daily_metrics_yaml(store: PregnancyDataStore, payload: dict[str, Any]) -> None:
    path = store.root / DAILY_METRICS_YAML
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, yaml.safe_dump(payload, allow_unicode=True, sort_keys=False))


def write_daily_metrics_markdown(store: PregnancyDataStore, payload: dict[str, Any]) -> None:
    path = store.root / DAILY_METRICS_MD
    lines = [
        "# Daily Metrics",
        "",
        "> Generated from official, non-private events. Raw conversation remains in inbox/events.",
        "",
        "## 体重趋势",
        "",
    ]
    trend = payload.get("weight_trend") or {}
    latest = trend.get("latest")
    previous = trend.get("previous")
    if latest:
        lines.append(f"- 最新：{format_weight(latest)} ({latest.get('date')}, source: {latest.get('source_event_id')})")
        if previous:
            lines.append(f"- 上次：{format_weight(previous)} ({previous.get('date')}, source: {previous.get('source_event_id')})")
            lines.append(f"- 变化：{trend.get('delta_kg')}kg")
    else:
        lines.append("- 暂无体重记录。")

    lines.extend(["", "## 血压趋势", ""])
    blood_pressure_trend = payload.get("blood_pressure_trend") or {}
    latest_blood_pressure = blood_pressure_trend.get("latest")
    previous_blood_pressure = blood_pressure_trend.get("previous")
    if latest_blood_pressure:
        lines.append(
            f"- 最新：{format_blood_pressure(latest_blood_pressure)} "
            f"({latest_blood_pressure.get('date')}, source: {latest_blood_pressure.get('source_event_id')})"
        )
        if previous_blood_pressure:
            lines.append(
                f"- 上次：{format_blood_pressure(previous_blood_pressure)} "
                f"({previous_blood_pressure.get('date')}, source: {previous_blood_pressure.get('source_event_id')})"
            )
            delta = blood_pressure_trend.get("delta") or {}
            lines.append(f"- 变化：收缩压 {delta.get('systolic')}，舒张压 {delta.get('diastolic')} mmHg")
    else:
        lines.append("- 暂无血压记录。")

    lines.extend(["", "## 最近日常记录", ""])
    days = payload.get("days") or {}
    if not days:
        lines.append("- 暂无。")
    for date, day in days.items():
        lines.append(f"### {date}")
        if day.get("weight"):
            lines.append(f"- 体重：{format_weight(day['weight'])}")
        for point in (day.get("blood_pressure_readings") or [])[-3:]:
            lines.append(f"- 血压：{format_blood_pressure(point)} (source: {point.get('source_event_id')})")
        append_entry_lines(lines, "心情", day.get("mood_entries") or [])
        append_entry_lines(lines, "饮食", day.get("diet_entries") or [])
        append_entry_lines(lines, "运动", day.get("activity_entries") or [])
        append_entry_lines(lines, "睡眠", day.get("sleep_entries") or [])
    atomic_write_text(path, "\n".join(lines) + "\n")


def append_entry_lines(lines: list[str], label: str, entries: list[dict[str, Any]]) -> None:
    for entry in entries[-3:]:
        lines.append(f"- {label}：{entry.get('summary', '')} (source: {entry.get('event_id')})")


def format_weight(point: dict[str, Any]) -> str:
    return f"{point.get('value')}{point.get('unit', 'kg')}"


def format_blood_pressure(point: dict[str, Any]) -> str:
    return f"{point.get('systolic')}/{point.get('diastolic')}{point.get('unit', 'mmHg')}"


def contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)
