from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

from .context_builder import format_gestational_age, read_events
from .doctor_questions import read_doctor_questions
from .medical_state import format_current_metric_line, read_current_medical_state
from .storage import PregnancyDataStore, SCHEMA_VERSION


CN_TZ = timezone(timedelta(hours=8))
VISIT_SOP_DIR = "reports/visit_sops"
DOCTOR_VISIT_NOTES_DIR = "reports/doctor_visit_notes"
FOLLOW_UP_KEYWORDS = ["复查", "下次", "预约", "产检", "门诊", "随访", "检查"]
ACTION_KEYWORDS = ["继续", "停止", "开始", "调整", "每天", "每周", "观察", "记录", "避免", "补充"]
UNCERTAINTY_KEYWORDS = ["不确定", "待", "需要确认", "问医生", "未说明", "不清楚"]


def generate_pre_visit_sop(
    store: PregnancyDataStore,
    visit_date: str,
    lookback_days: int = 14,
) -> Path:
    store.ensure_dirs()
    profile = store.load_profile()
    events = recent_visible_events(store, visit_date=visit_date, lookback_days=lookback_days)
    medical_state = read_current_medical_state(store)
    daily_metrics = read_yaml_if_exists(store.root / "memory" / "daily_metrics.yaml")
    questions = read_doctor_questions(store, statuses={"open", "asked"})

    lines = [
        f"# 产检前问诊 SOP {visit_date}",
        "",
        "> 由 Pregnancy Copilot Skill 根据本地结构化记忆生成。用于就诊前整理材料和问题，不替代医生判断。",
        "",
        "## 基础信息",
        "",
        f"- 当前孕周：{format_gestational_age(profile.get('current_gestational_age'))}",
        f"- 预计就诊日期：{visit_date}",
        f"- 数据窗口：就诊日前 {lookback_days} 天内的非 private 事件 + 当前医学状态索引",
        "",
        "## 当前有效医学状态",
        "",
    ]
    append_medical_state(lines, medical_state)
    lines.extend(["", "## 近期日常变化", ""])
    append_daily_metrics(lines, daily_metrics)
    lines.extend(["", "## 最近需要带给医生看的事项", ""])
    append_recent_medical_events(lines, events)
    lines.extend(["", "## 待问医生问题", ""])
    append_questions(lines, questions)
    lines.extend(
        [
            "",
            "## 就诊携带清单",
            "",
            "- 最近一次产检/化验/B 超报告原件或截图。",
            "- 本文件中的待问问题。",
            "- 最近症状、用药、体重/血压/血糖等记录。",
            "- 医生回复后，把原话录入 Skill，再生成检查后行动 SOP。",
            "",
            "## 使用边界",
            "",
            "- 当前医学判断应优先读取 `memory/current_medical_state.yaml` 的 current 字段。",
            "- 历史值用于趋势对比，不应覆盖最新同指标数据。",
            "- 不确定、缺失或医生未确认的信息，应直接标记待补充。",
        ]
    )
    return write_visit_sop(store, f"pre_visit_{visit_date}.md", lines)


def generate_post_visit_action_sop(
    store: PregnancyDataStore,
    visit_date: str,
    doctor_note: str,
    source: str = "doctor_note",
) -> dict[str, Path]:
    store.ensure_dirs()
    clean_note = doctor_note.strip()
    if not clean_note:
        raise ValueError("doctor_note must not be empty")

    note_path = save_doctor_visit_note(store, visit_date, clean_note, source)
    event = build_doctor_visit_event(visit_date, clean_note, source, note_path)
    store.append_event(event, dedupe_by_event_id=True)

    actions = extract_keyword_lines(clean_note, ACTION_KEYWORDS)
    follow_ups = extract_keyword_lines(clean_note, FOLLOW_UP_KEYWORDS)
    uncertainties = extract_keyword_lines(clean_note, UNCERTAINTY_KEYWORDS)

    lines = [
        f"# 检查后行动 SOP {visit_date}",
        "",
        "> 基于用户录入的医生回复/就诊记录整理。请以医生原始意见为准；Skill 只做归档、拆解和提醒。",
        "",
        "## 医生回复原文",
        "",
        clean_note,
        "",
        "## 本阶段行动",
        "",
    ]
    append_bullets(lines, actions, fallback="暂无明确行动句。请补充医生原话或手动拆分。")
    lines.extend(["", "## 复查与下次产检", ""])
    append_bullets(lines, follow_ups, fallback="暂无明确复查/下次产检信息。")
    lines.extend(["", "## 待补充或待确认", ""])
    append_bullets(lines, uncertainties, fallback="暂无显式不确定项；如仍不清楚，应继续追问医生。")
    lines.extend(
        [
            "",
            "## 记忆更新提示",
            "",
            "- 如果本次医生确认了新的检查数值，请用 `record_medical_observation` 录入结构化指标。",
            "- 如果本次医生回复刷新了旧结论，保留旧值为历史，但以后回答应以最新 current 指标为准。",
            "- 如果医生给了明确复查时间，把它写入后续提醒或日历系统。",
        ]
    )
    sop_path = write_visit_sop(store, f"post_visit_{visit_date}.md", lines)
    return {"note_path": note_path, "sop_path": sop_path}


def recent_visible_events(
    store: PregnancyDataStore,
    visit_date: str,
    lookback_days: int,
) -> list[dict[str, Any]]:
    end = datetime.fromisoformat(visit_date).date()
    start = end - timedelta(days=lookback_days)
    result = []
    for event in read_events(store):
        if event.get("import_status") == "draft" or event.get("privacy_level") == "private":
            continue
        timestamp = str(event.get("timestamp", ""))
        if len(timestamp) < 10:
            continue
        event_date = datetime.fromisoformat(timestamp[:10]).date()
        if start <= event_date <= end:
            result.append(event)
    return result


def append_medical_state(lines: list[str], medical_state: dict[str, Any]) -> None:
    metrics = medical_state.get("metrics") or {}
    if not metrics:
        lines.append("- 暂无结构化医学指标。")
        return
    for metric in metrics.values():
        current = metric.get("current") or {}
        if not current:
            continue
        lines.append(f"- {format_current_metric_line(current)}")
        source = current.get("raw_source_path") or current.get("source_event_id")
        if source:
            lines.append(f"  - 来源：{source}")
        previous_values = metric.get("previous_values") or []
        if previous_values:
            history = "；".join(
                f"{item.get('measured_at', 'unknown')} {item.get('value')}{item.get('unit', '')}"
                for item in previous_values[-3:]
            )
            lines.append(f"  - 历史对比：{history}")


def append_daily_metrics(lines: list[str], daily_metrics: dict[str, Any]) -> None:
    if not daily_metrics:
        lines.append("- 暂无体重、血压、心情、饮食、运动或睡眠索引。")
        return
    trend = daily_metrics.get("weight_trend") or {}
    latest = trend.get("latest")
    if latest:
        lines.append(f"- 最新体重：{latest.get('value')}{latest.get('unit', 'kg')}（{latest.get('date')}）")
        if trend.get("delta_kg") is not None:
            lines.append(f"  - 较上次变化：{trend.get('delta_kg')}kg")
    days = daily_metrics.get("days") or {}
    recent_entries = []
    for date, day in list(days.items())[-7:]:
        for key, label in [
            ("mood_entries", "心情"),
            ("sleep_entries", "睡眠"),
            ("activity_entries", "运动"),
            ("diet_entries", "饮食"),
        ]:
            for entry in day.get(key) or []:
                recent_entries.append(f"{date} {label}：{entry.get('summary')}")
    if recent_entries:
        lines.extend(f"- {entry}" for entry in recent_entries[-8:])
    if not latest and not recent_entries:
        lines.append("- 暂无近期日常摘要。")


def append_recent_medical_events(lines: list[str], events: list[dict[str, Any]]) -> None:
    selected = [
        event
        for event in events
        if event.get("triage_required") is True
        or event.get("risk_level") in {"yellow", "red"}
        or event.get("event_type") in {"prenatal_report", "report_question", "medication_question"}
    ]
    if not selected:
        lines.append("- 暂无近期需要特别带给医生看的事项。")
        return
    for event in selected[-12:]:
        summary = event.get("user_message_summary") or event.get("event_id", "")
        risk = event.get("risk_level", "unknown")
        source = event.get("raw_source_path") or event.get("source") or ""
        lines.append(f"- {event.get('timestamp', 'unknown')} [{risk}] {summary}")
        if source:
            lines.append(f"  - 来源：{source}")


def append_questions(lines: list[str], questions: list[dict[str, Any]]) -> None:
    if not questions:
        lines.append("- 暂无待问医生问题。")
        return
    for index, question in enumerate(questions, start=1):
        text = question.get("question", "")
        status = question.get("status", "open")
        risk = question.get("risk_level")
        suffix = f"（{status}"
        if risk:
            suffix += f", {risk}"
        suffix += "）"
        lines.append(f"{index}. {text}{suffix}")


def save_doctor_visit_note(store: PregnancyDataStore, visit_date: str, doctor_note: str, source: str) -> Path:
    path = store.root / DOCTOR_VISIT_NOTES_DIR / f"{visit_date}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "---",
        f"schema_version: {SCHEMA_VERSION}",
        f"visit_date: {visit_date}",
        f"source: {source}",
        "---",
        "",
        doctor_note,
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def build_doctor_visit_event(visit_date: str, doctor_note: str, source: str, note_path: Path) -> dict[str, Any]:
    digest = hashlib.sha256(f"{visit_date}|{source}|{doctor_note}".encode("utf-8")).hexdigest()[:16]
    return {
        "schema_version": SCHEMA_VERSION,
        "event_id": f"doctor-visit-{visit_date}-{digest}",
        "event_type": "doctor_visit_summary",
        "mode": "medical_record",
        "timestamp": f"{visit_date}T12:00:00+08:00",
        "source": source,
        "raw_source_path": str(note_path),
        "user_message_summary": first_sentence(doctor_note),
        "risk_level": "not_applicable",
        "triage_required": False,
        "privacy_level": "summary",
        "created_at": datetime.now(tz=CN_TZ).isoformat(),
    }


def extract_keyword_lines(text: str, keywords: list[str]) -> list[str]:
    lines = split_note_lines(text)
    matches = []
    for line in lines:
        if any(keyword in line for keyword in keywords):
            matches.append(line)
    return dedupe_preserve_order(matches)


def split_note_lines(text: str) -> list[str]:
    raw_lines = []
    for line in text.splitlines():
        raw_lines.extend(re.split(r"[。；;]", line))
    return [re.sub(r"^\s*[-*0-9.、）)]+\s*", "", item).strip() for item in raw_lines if item.strip()]


def first_sentence(text: str, max_length: int = 120) -> str:
    lines = split_note_lines(text)
    if not lines:
        return text[:max_length]
    sentence = lines[0]
    return sentence if len(sentence) <= max_length else sentence[: max_length - 1] + "…"


def dedupe_preserve_order(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        key = re.sub(r"\s+", "", item)
        if key and key not in seen:
            seen.add(key)
            result.append(item)
    return result


def append_bullets(lines: list[str], items: list[str], fallback: str) -> None:
    if not items:
        lines.append(f"- {fallback}")
        return
    lines.extend(f"- {item}" for item in items)


def read_yaml_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def write_visit_sop(store: PregnancyDataStore, filename: str, lines: list[str]) -> Path:
    path = store.root / VISIT_SOP_DIR / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
