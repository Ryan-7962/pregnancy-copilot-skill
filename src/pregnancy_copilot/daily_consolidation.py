from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
import json
import re

import yaml

from .artifacts import generate_daily_log
from .context_builder import build_current_context, build_emotional_pattern, build_medical_timeline, read_events
from .daily_metrics import build_daily_metrics_index
from .doctor_questions import read_doctor_questions
from .medical_state import rebuild_current_medical_state
from .storage import PregnancyDataStore, SCHEMA_VERSION, atomic_write_text


@dataclass(frozen=True)
class DailyConsolidationResult:
    date: str
    daily_log_path: Path
    index_path: Path
    message_count: int
    event_count: int


def consolidate_day(
    store: PregnancyDataStore,
    date: str,
    ai_summary: str | None = None,
    ai_summary_source: str = "host_llm",
) -> DailyConsolidationResult:
    validate_date(date)
    store.ensure_dirs()

    raw_paths = raw_message_paths_for_date(store, date)
    message_count = sum(count_raw_messages(path) for path in raw_paths)
    events = [event for event in read_events(store) if str(event.get("timestamp", "")).startswith(date)]
    visible_events = [event for event in events if event.get("privacy_level") != "private"]
    private_events = [event for event in events if event.get("privacy_level") == "private"]

    rebuild_current_medical_state(store)
    build_daily_metrics_index(store)
    build_current_context(store, as_of=date)
    build_medical_timeline(store)
    build_emotional_pattern(store)

    daily_log_path = generate_daily_log(store, date)
    append_conversation_coverage(
        daily_log_path,
        store,
        message_count=message_count,
        raw_paths=raw_paths,
        ai_summary=ai_summary,
        ai_summary_source=ai_summary_source,
    )

    index_path = store.root / "memory" / "daily_conversation_index.yaml"
    with store.transaction_lock("daily-conversation-index"):
        index = read_daily_index(index_path)
        index["days"][date] = build_day_index(
            store=store,
            date=date,
            message_count=message_count,
            raw_paths=raw_paths,
            events=events,
            visible_events=visible_events,
            private_events=private_events,
            ai_summary=ai_summary,
            ai_summary_source=ai_summary_source,
        )
        index["days"] = {key: index["days"][key] for key in sorted(index["days"])}
        atomic_write_text(index_path, yaml.safe_dump(index, allow_unicode=True, sort_keys=False))

    return DailyConsolidationResult(
        date=date,
        daily_log_path=daily_log_path,
        index_path=index_path,
        message_count=message_count,
        event_count=len(events),
    )


def build_day_index(
    *,
    store: PregnancyDataStore,
    date: str,
    message_count: int,
    raw_paths: list[Path],
    events: list[dict[str, Any]],
    visible_events: list[dict[str, Any]],
    private_events: list[dict[str, Any]],
    ai_summary: str | None,
    ai_summary_source: str,
) -> dict[str, Any]:
    intents = Counter(str(event.get("intent")) for event in visible_events if event.get("intent"))
    risks = Counter(
        str(event.get("risk_level"))
        for event in visible_events
        if event.get("risk_level") in {"green", "yellow", "red"}
    )
    medical_count = sum(
        1
        for event in visible_events
        if event.get("triage_required") is True or event.get("intent") in {"report_review", "medication"}
    )
    mood_count = sum(1 for event in visible_events if event.get("intent") == "mood_support")
    summary = None
    if ai_summary and ai_summary.strip():
        summary = {
            "status": "ai_organized",
            "source": ai_summary_source,
            "text": ai_summary.strip(),
            "medical_fact_effect": "none",
        }
    external_sources = external_sources_for_date(store, date)
    return {
        "message_count": message_count,
        "event_count": len(events),
        "private_event_count": len(private_events),
        "medical_event_count": medical_count,
        "mood_event_count": mood_count,
        "intents": dict(sorted(intents.items())),
        "risk_counts": dict(sorted(risks.items())),
        "open_doctor_question_count": len(read_doctor_questions(store, statuses={"open", "asked"})),
        "external_source_count": len(external_sources),
        "external_sources": external_sources,
        "raw_source_paths": [path.relative_to(store.root).as_posix() for path in raw_paths],
        "daily_log_path": f"daily_logs/{date}.md",
        "ai_summary": summary,
    }


def raw_message_paths_for_date(store: PregnancyDataStore, date: str) -> list[Path]:
    return sorted(path for path in (store.root / "inbox").glob(f"raw_*_messages/{date}.md") if path.is_file())


def count_raw_messages(path: Path) -> int:
    return len(re.findall(r"(?m)^timestamp:\s*", path.read_text(encoding="utf-8")))


def append_conversation_coverage(
    daily_log_path: Path,
    store: PregnancyDataStore,
    *,
    message_count: int,
    raw_paths: list[Path],
    ai_summary: str | None,
    ai_summary_source: str,
) -> None:
    base = daily_log_path.read_text(encoding="utf-8").rstrip()
    lines = [base, "", "## 今日对话覆盖", "", f"- 共 {message_count} 条本地原文记录。"]
    if raw_paths:
        lines.extend(f"- source: {path.relative_to(store.root).as_posix()}" for path in raw_paths)
    else:
        lines.append("- 暂无原文记录。")
    lines.extend(["", "## AI 整理摘要", ""])
    if ai_summary and ai_summary.strip():
        lines.extend(
            [
                f"> [ai_organized] source: {ai_summary_source}; this summary does not update medical facts.",
                "",
                ai_summary.strip(),
            ]
        )
    else:
        lines.append("- 未提供宿主 LLM 摘要；没有从原文自动推断事实。")
    atomic_write_text(daily_log_path, "\n".join(lines) + "\n")


def read_daily_index(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": SCHEMA_VERSION, "days": {}}
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Unsupported daily conversation index schema version")
    return {"schema_version": SCHEMA_VERSION, "days": dict(payload.get("days") or {})}


def validate_date(value: str) -> None:
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(f"Invalid date: {value!r}") from exc


def external_sources_for_date(store: PregnancyDataStore, date: str) -> list[dict[str, str]]:
    path = store.root / "external_sources" / "index.jsonl"
    if not path.exists():
        return []
    sources: dict[str, dict[str, str]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("event_type") != "capture" or not str(event.get("captured_at", "")).startswith(date):
            continue
        source_id = str(event.get("source_id") or "")
        record_path = str(event.get("raw_path") or "")
        if source_id and record_path:
            sources[source_id] = {"source_id": source_id, "record_path": record_path}
    return [sources[source_id] for source_id in sorted(sources)]
