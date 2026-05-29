from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from .storage import PregnancyDataStore, SCHEMA_VERSION


CN_TZ = timezone(timedelta(hours=8))
VALID_STATUSES = {"open", "asked", "answered", "archived"}
ACTIVE_STATUSES = {"open", "asked"}


def questions_jsonl_path(store: PregnancyDataStore) -> Path:
    store.ensure_dirs()
    return store.root / "doctor_questions" / "questions.jsonl"


def questions_markdown_path(store: PregnancyDataStore) -> Path:
    store.ensure_dirs()
    return store.root / "doctor_questions" / "questions.md"


def read_doctor_questions(
    store: PregnancyDataStore,
    statuses: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    path = questions_jsonl_path(store)
    if not path.exists():
        return []
    allowed = set(statuses) if statuses is not None else None
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if allowed is None or record.get("status") in allowed:
            records.append(record)
    return records


def add_question_candidates(store: PregnancyDataStore, event: dict[str, Any]) -> list[dict[str, Any]]:
    questions = list(event.get("doctor_question_candidates") or [])
    if event.get("mode") == "doctor_questions" and event.get("user_message_summary"):
        questions.insert(0, event["user_message_summary"])
    questions = dedupe_questions(questions)
    if not questions:
        return []

    existing = read_doctor_questions(store)
    existing_keys = {normalize_question(record.get("question", "")) for record in existing}
    new_records = []
    for index, question in enumerate(questions, start=1):
        key = normalize_question(question)
        if not key or key in existing_keys:
            continue
        record = {
            "schema_version": SCHEMA_VERSION,
            "question_id": build_question_id(event.get("event_id", "event"), index, question),
            "question": question.strip(),
            "status": "open",
            "created_at": event.get("timestamp") or now_iso(),
            "updated_at": event.get("timestamp") or now_iso(),
            "source_event_id": event.get("event_id"),
            "source": event.get("source"),
            "raw_source_path": event.get("raw_source_path"),
            "gestational_age": event.get("gestational_age"),
            "risk_level": event.get("risk_level"),
            "answer_summary": None,
        }
        new_records.append(record)
        existing_keys.add(key)

    if new_records:
        path = questions_jsonl_path(store)
        with path.open("a", encoding="utf-8") as handle:
            for record in new_records:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return new_records


def update_question_status(
    store: PregnancyDataStore,
    question_id: str,
    status: str,
    answer_summary: str | None = None,
    updated_at: str | None = None,
) -> dict[str, Any]:
    if status not in VALID_STATUSES:
        raise ValueError(f"Unsupported doctor question status: {status!r}")
    records = read_doctor_questions(store)
    updated = None
    for record in records:
        if record.get("question_id") == question_id:
            record["status"] = status
            record["updated_at"] = updated_at or now_iso()
            if answer_summary is not None:
                record["answer_summary"] = answer_summary
            updated = record
            break
    if updated is None:
        raise KeyError(question_id)
    write_question_records(store, records)
    return updated


def write_question_records(store: PregnancyDataStore, records: list[dict[str, Any]]) -> Path:
    path = questions_jsonl_path(store)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path


def render_doctor_questions_markdown(
    store: PregnancyDataStore,
    statuses: Iterable[str] = ACTIVE_STATUSES,
) -> Path:
    records = read_doctor_questions(store, statuses=statuses)
    lines = [
        "# Doctor Questions",
        "",
        "> Generated from message events. Review with an obstetric doctor; this is not medical advice.",
        "",
    ]
    if records:
        for record in records:
            lines.append(f"- [{record.get('status', 'open')}] {record.get('question', '')}")
            source = record.get("source_event_id") or record.get("raw_source_path")
            if source:
                lines.append(f"  - source: {source}")
    else:
        lines.append("- 暂无待问问题。")
    path = questions_markdown_path(store)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def dedupe_questions(questions: Iterable[str]) -> list[str]:
    seen = set()
    result = []
    for question in questions:
        text = " ".join(str(question).split())
        key = normalize_question(text)
        if text and key not in seen:
            seen.add(key)
            result.append(text)
    return result


def normalize_question(question: str) -> str:
    return re.sub(r"\s+", "", question).strip("？?。.!！").lower()


def build_question_id(event_id: str, index: int, question: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", event_id).strip("-").lower() or "event"
    return f"dq-{slug}-{index}-{abs(hash(normalize_question(question))) % 100000:05d}"


def now_iso() -> str:
    return datetime.now(tz=CN_TZ).isoformat()
