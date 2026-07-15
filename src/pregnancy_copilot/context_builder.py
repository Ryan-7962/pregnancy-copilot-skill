from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from .doctor_questions import read_doctor_questions
from .medical_state import format_current_metric_line, read_current_medical_state
from .pregnancy_time import calculate_gestational_age
from .storage import PregnancyDataStore, atomic_write_text


MEDICAL_EVENT_TYPES = {"prenatal_report", "report_question", "medication_question"}
EMOTION_KEYWORDS = ["焦虑", "担心", "害怕", "紧张", "崩溃", "难过", "压力", "安心", "情绪", "心情"]


def format_gestational_age(value: Any) -> str:
    if not value:
        return "未设置"
    text = str(value)
    match = re.fullmatch(r"(\d+)w(\d+)d", text, flags=re.IGNORECASE)
    if match:
        return f"W{match.group(1)}+{match.group(2)}"
    return text


def read_events(store: PregnancyDataStore, filename: str = "events.jsonl") -> list[dict[str, Any]]:
    path = store.root / "events" / filename
    if not path.exists():
        return []

    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(json.loads(line))
    return events


def build_current_context(store: PregnancyDataStore, recent_limit: int = 20, as_of: str | None = None) -> Path:
    store.ensure_dirs()
    profile = store.load_profile()
    events = read_events(store)
    official_events = [event for event in events if event.get("import_status") != "draft"]
    live_events = [event for event in official_events if event.get("source") != "gemini_import"][-recent_limit:]
    imported_events = [
        event
        for event in official_events
        if event.get("source") == "gemini_import" and event.get("risk_level") == "green"
    ]
    recent_events = (live_events or official_events[-recent_limit:])

    gestational_age = format_gestational_age(calculate_gestational_age(profile, as_of=as_of))
    focus_items = profile.get("current_focus") or []
    if not focus_items:
        focus_items = ["暂无重点事项，请从后续事件中更新。"]
    medical_state = read_current_medical_state(store)

    doctor_questions = []
    for event in recent_events:
        doctor_questions.extend(event.get("doctor_question_candidates") or [])
    doctor_questions.extend(record.get("question", "") for record in read_doctor_questions(store, statuses={"open", "asked"}))

    lines = [
        "# Current Context",
        "",
        "> This file is generated from profile and append-only events.",
        "",
        "## 当前孕周",
        "",
        gestational_age,
        "",
        "## 当前重点",
        "",
    ]
    lines.extend(f"- {item}" for item in focus_items)

    lines.extend(["", "## 当前有效医学状态", ""])
    append_current_medical_state_lines(lines, medical_state)

    lines.extend(["", "## 高频日常指标摘要", ""])
    append_daily_metrics_lines(lines, store)

    lines.extend(["", "## 来源可信度摘要", ""])
    append_source_confidence_lines(lines, store)

    lines.extend(["", "## 待核对事项", ""])
    append_open_review_lines(lines, store)

    lines.extend(["", "## 最近实时事件", ""])
    if live_events:
        append_event_lines(lines, live_events)
    else:
        lines.append("暂无事件。")

    lines.extend(["", "## 历史导入低风险模式", ""])
    if imported_events:
        counts = Counter(event.get("event_type", "unknown") for event in imported_events)
        lines.append("### 类型分布")
        lines.extend(f"- {name}: {count}" for name, count in counts.most_common())
        lines.extend(["", "### 代表性低风险主题"])
        for event in imported_events[-5:]:
            summary = event.get("user_message_summary") or event.get("event_id", "未命名事件")
            source = event.get("raw_source_path", "unknown")
            lines.append(f"- {summary} (source: {source})")
    else:
        lines.append("暂无已晋升的低风险历史导入事件。")

    lines.extend(["", "## 最近事件", ""])
    if recent_events:
        append_event_lines(lines, recent_events)
    else:
        lines.append("暂无事件。")

    lines.extend(["", "## 下次产检待问问题", ""])
    if doctor_questions:
        seen = set()
        for question in doctor_questions:
            if question not in seen:
                seen.add(question)
                lines.append(f"- {question}")
    else:
        lines.append("- 暂无。")

    lines.extend(
        [
            "",
            "## 可追溯原则",
            "",
            "- 医学事实必须来自 events、reports 或医生原文，并保留 source path。",
            "- Gemini 历史只能作为线索；未核验内容不得覆盖 current_medical_state。",
        ]
    )

    path = store.root / "memory" / "current_context.md"
    atomic_write_text(path, "\n".join(lines) + "\n")
    return path


def append_current_medical_state_lines(lines: list[str], medical_state: dict[str, Any]) -> None:
    metrics = medical_state.get("metrics") or {}
    if not metrics:
        lines.append("- 暂无结构化医学指标。")
        return
    for metric in metrics.values():
        current = metric.get("current") or {}
        if current:
            lines.append(f"- {format_current_metric_line(current)}")
            lines.append(
                f"  - 当前值时间：{current.get('measured_at', 'unknown')}；"
                f"来源：{current.get('raw_source_path') or current.get('source_event_id') or 'unknown'}；"
                f"来源置信：{current.get('source_confidence', 'unknown')}"
            )
            if current.get("status") == "resolved":
                lines.append("  - 旧值已被更新，不应作为当前判断依据。")
        previous_values = metric.get("previous_values") or []
        if previous_values:
            previous_text = "；".join(
                f"{item.get('measured_at', 'unknown')} {item.get('value')}{item.get('unit', '')}"
                for item in previous_values[-3:]
            )
            lines.append(f"  - 历史值：{previous_text}")
        candidates = metric.get("candidates") or []
        if candidates:
            candidate_text = "；".join(
                f"{item.get('measured_at', 'unknown')} {item.get('value')}{item.get('unit', '')}"
                f" ({item.get('candidate_reason', 'needs_review')})"
                for item in candidates[-3:]
            )
            lines.append(f"  - 待确认候选：{candidate_text}")


def append_daily_metrics_lines(lines: list[str], store: PregnancyDataStore) -> None:
    path = store.root / "memory" / "daily_metrics.yaml"
    if not path.exists():
        lines.append("- 暂无体重、血压、心情、饮食、运动或睡眠摘要索引。")
        return
    import yaml

    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    trend = payload.get("weight_trend") or {}
    latest = trend.get("latest")
    if latest:
        lines.append(f"- 最新体重：{latest.get('value')}{latest.get('unit', 'kg')}（{latest.get('date')}）")
        if trend.get("delta_kg") is not None:
            lines.append(f"  - 较上次变化：{trend.get('delta_kg')}kg")
    blood_pressure_trend = payload.get("blood_pressure_trend") or {}
    latest_blood_pressure = blood_pressure_trend.get("latest")
    if latest_blood_pressure:
        lines.append(
            f"- 最新血压：{latest_blood_pressure.get('systolic')}/"
            f"{latest_blood_pressure.get('diastolic')}{latest_blood_pressure.get('unit', 'mmHg')}"
            f"（{latest_blood_pressure.get('date')}）"
        )
    days = payload.get("days") or {}
    recent_moods = []
    for date, day in list(days.items())[-7:]:
        for entry in day.get("mood_entries") or []:
            recent_moods.append(f"{date}：{entry.get('summary')}")
    if recent_moods:
        lines.append("- 最近心情：")
        lines.extend(f"  - {item}" for item in recent_moods[-3:])
    if not latest and not latest_blood_pressure and not recent_moods:
        lines.append("- 暂无体重、血压或心情摘要。")


def append_source_confidence_lines(lines: list[str], store: PregnancyDataStore) -> None:
    path = store.root / "memory" / "source_confidence.yaml"
    if not path.exists():
        lines.append("- 暂无来源可信度索引。")
        return
    import yaml

    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    summary = payload.get("summary") or {}
    if summary:
        for key in ["report_verified", "user_reported", "gemini_inferred", "needs_review"]:
            if key in summary:
                lines.append(f"- {key}: {summary.get(key)}")
    entries = payload.get("entries") or []
    if entries:
        lines.append("- 最近线索：")
        for entry in entries[-5:]:
            lines.append(
                f"  - {entry.get('topic')}: {entry.get('statement')} "
                f"({entry.get('confidence')}, source: {entry.get('source_file')})"
            )


def append_open_review_lines(lines: list[str], store: PregnancyDataStore) -> None:
    path = store.root / "memory" / "open_review_items.yaml"
    if not path.exists():
        lines.append("- 暂无待核对事项。")
        return
    import yaml

    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    items = payload.get("items") or []
    if not items:
        lines.append("- 暂无待核对事项。")
        return
    for item in items[:10]:
        lines.append(
            f"- [{item.get('priority', 'unknown')}] {item.get('item')}: "
            f"{item.get('signal', '')}；核对原因：{item.get('why_review', '')}"
        )


def build_medical_timeline(store: PregnancyDataStore) -> Path:
    store.ensure_dirs()
    events = [event for event in read_events(store) if event.get("import_status") != "draft"]
    medical_events = [
        event
        for event in events
        if event.get("event_type") in MEDICAL_EVENT_TYPES or event.get("risk_level") in {"yellow", "red"}
    ]
    lines = [
        "# Medical Timeline",
        "",
        "> Generated from reviewed/official events. Draft imports are excluded.",
        "",
        "| Date | GA | Risk | Event | Source |",
        "|---|---:|---|---|---|",
    ]
    if medical_events:
        for event in medical_events:
            lines.append(
                "| {date} | {ga} | {risk} | {summary} | {source} |".format(
                    date=str(event.get("timestamp", "unknown"))[:10],
                    ga=format_gestational_age(event.get("gestational_age")),
                    risk=event.get("risk_level", "unknown"),
                    summary=escape_table_text(event.get("user_message_summary") or event.get("event_id", "")),
                    source=escape_table_text(event.get("raw_source_path", "unknown")),
                )
            )
    else:
        lines.append("| TBD | TBD | TBD | 暂无已确认医学事件 | reports/ |")
    path = store.root / "memory" / "medical_timeline.md"
    atomic_write_text(path, "\n".join(lines) + "\n")
    return path


def build_emotional_pattern(store: PregnancyDataStore, recent_limit: int = 20) -> Path:
    store.ensure_dirs()
    events = [event for event in read_events(store) if event.get("import_status") != "draft"]
    emotion_events = [
        event
        for event in events
        if contains_emotion_signal(event.get("user_message_summary", ""))
        or contains_emotion_signal(event.get("assistant_response_summary", ""))
    ][-recent_limit:]
    lines = [
        "# Emotional Pattern",
        "",
        "> Generated from official events. Private raw text is not expanded here.",
        "",
        "## 已知触发点",
        "",
    ]
    if emotion_events:
        for event in emotion_events:
            lines.append(
                f"- {event.get('timestamp', 'unknown')}：{event.get('user_message_summary', event.get('event_id', ''))}"
            )
    else:
        lines.append("- 暂无真实数据。")
    lines.extend(["", "## 回答风格偏好", "", "- 温柔", "- 清晰", "- 不敷衍", "- 先接住情绪，再回到事实和行动"])
    if emotion_events:
        lines.extend(["", "## 有效安抚线索", ""])
        seen = set()
        for event in emotion_events:
            response = event.get("assistant_response_summary")
            if response and response not in seen:
                seen.add(response)
                lines.append(f"- {response}")
    path = store.root / "memory" / "emotional_pattern.md"
    atomic_write_text(path, "\n".join(lines) + "\n")
    return path


def append_event_lines(lines: list[str], events: list[dict[str, Any]]) -> None:
    for event in events:
        summary = event.get("user_message_summary") or event.get("event_id", "未命名事件")
        response_summary = event.get("assistant_response_summary")
        risk = event.get("risk_level", "unknown")
        source = event.get("raw_source_path", "unknown")
        lines.append(f"- {event.get('timestamp', 'unknown')} [{risk}] {summary} (source: {source})")
        if response_summary:
            lines.append(f"  - AI 摘要：{response_summary}")


def contains_emotion_signal(text: str) -> bool:
    return any(keyword in text for keyword in EMOTION_KEYWORDS)


def escape_table_text(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")
