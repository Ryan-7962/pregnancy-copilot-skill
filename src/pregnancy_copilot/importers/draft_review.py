from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


AUTO_PROMOTE_EVENT_TYPES = {"diet_question", "symptom_qa", "care_plan_question"}


@dataclass
class DraftReview:
    total: int = 0
    auto_promotable: int = 0
    manual_required: int = 0
    by_event_type: Counter = field(default_factory=Counter)
    by_risk_level: Counter = field(default_factory=Counter)


@dataclass
class PromotionResult:
    promoted: int = 0
    skipped_manual: int = 0
    duplicates: int = 0
    report_path: Path | None = None
    events_path: Path | None = None


@dataclass
class DecisionResult:
    promoted: int = 0
    skipped: int = 0
    corrections_needed: int = 0
    unchecked: int = 0
    duplicates: int = 0
    report_path: Path | None = None
    events_path: Path | None = None
    correction_drafts_path: Path | None = None


def review_import_drafts(draft_path: str | Path) -> DraftReview:
    review = DraftReview()
    for event in read_jsonl(Path(draft_path)):
        review.total += 1
        review.by_event_type[event.get("event_type", "unknown")] += 1
        review.by_risk_level[event.get("risk_level", "unknown")] += 1
        if is_auto_promotable(event):
            review.auto_promotable += 1
        else:
            review.manual_required += 1
    return review


def promote_import_drafts(data_root: str | Path, draft_path: str | Path | None = None) -> PromotionResult:
    root = Path(data_root)
    draft_path = Path(draft_path) if draft_path else root / "events" / "draft_import_events.jsonl"
    events_path = root / "events" / "events.jsonl"
    report_path = root / "exports" / "draft_review_report.md"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    existing_ids = {event.get("event_id") for event in read_jsonl(events_path)}
    result = PromotionResult(events_path=events_path, report_path=report_path)
    promoted_rows = []

    for event in read_jsonl(draft_path):
        event_id = event.get("event_id")
        if event_id in existing_ids:
            result.duplicates += 1
            continue
        if not is_auto_promotable(event):
            result.skipped_manual += 1
            continue
        promoted = dict(event)
        promoted["import_status"] = "promoted"
        promoted["promoted_from"] = "draft_import_events.jsonl"
        promoted_rows.append(promoted)
        existing_ids.add(event_id)
        result.promoted += 1

    if promoted_rows:
        with events_path.open("a", encoding="utf-8") as handle:
            for row in promoted_rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    review = review_import_drafts(draft_path)
    report_path.write_text(render_review_report(review, result), encoding="utf-8")
    return result


def generate_manual_review_queue(data_root: str | Path, draft_path: str | Path | None = None) -> Path:
    root = Path(data_root)
    draft_path = Path(draft_path) if draft_path else root / "events" / "draft_import_events.jsonl"
    queue_path = root / "exports" / "manual_review_queue.md"
    queue_path.parent.mkdir(parents=True, exist_ok=True)

    manual_events = [event for event in read_jsonl(draft_path) if not is_auto_promotable(event)]
    manual_events.sort(key=manual_review_sort_key)
    queue_path.write_text(render_manual_review_queue(manual_events), encoding="utf-8")
    return queue_path


def apply_manual_review_decisions(
    data_root: str | Path,
    queue_path: str | Path | None = None,
    draft_path: str | Path | None = None,
) -> DecisionResult:
    root = Path(data_root)
    queue_path = Path(queue_path) if queue_path else root / "exports" / "manual_review_queue.md"
    draft_path = Path(draft_path) if draft_path else root / "events" / "draft_import_events.jsonl"
    events_path = root / "events" / "events.jsonl"
    correction_drafts_path = root / "events" / "correction_drafts.jsonl"
    report_path = root / "exports" / "manual_review_decisions_report.md"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    decisions = parse_manual_review_decisions(queue_path.read_text(encoding="utf-8"))
    drafts = {event.get("event_id"): event for event in read_jsonl(draft_path)}
    existing_ids = {event.get("event_id") for event in read_jsonl(events_path)}
    result = DecisionResult(events_path=events_path, correction_drafts_path=correction_drafts_path, report_path=report_path)
    promoted_rows = []
    correction_rows = []

    for event_id, decision in decisions.items():
        event = drafts.get(event_id)
        if not event:
            continue
        if decision == "promote":
            if event_id in existing_ids:
                result.duplicates += 1
                continue
            promoted = dict(event)
            promoted["import_status"] = "promoted_manual"
            promoted["promoted_from"] = "manual_review_queue.md"
            promoted_rows.append(promoted)
            existing_ids.add(event_id)
            result.promoted += 1
        elif decision == "skip":
            result.skipped += 1
        elif decision == "correction needed":
            correction_rows.append(
                {
                    "schema_version": event.get("schema_version", "0.1"),
                    "event_id": f"correction-draft-{event_id}",
                    "event_type": "correction_draft",
                    "target_event_id": event_id,
                    "source": "manual_review_queue",
                    "raw_source_path": event.get("raw_source_path"),
                    "reason": "manual_review_marked_correction_needed",
                    "status": "draft",
                }
            )
            result.corrections_needed += 1
        else:
            result.unchecked += 1

    if promoted_rows:
        with events_path.open("a", encoding="utf-8") as handle:
            for row in promoted_rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    if correction_rows:
        with correction_drafts_path.open("a", encoding="utf-8") as handle:
            for row in correction_rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    report_path.write_text(render_decisions_report(result), encoding="utf-8")
    return result


def is_auto_promotable(event: dict[str, Any]) -> bool:
    if event.get("requires_manual_review"):
        return False
    if event.get("risk_level") != "green":
        return False
    return event.get("event_type") in AUTO_PROMOTE_EVENT_TYPES


def manual_review_sort_key(event: dict[str, Any]) -> tuple[int, str]:
    risk_order = {"red": 0, "yellow": 1, "green": 4}
    type_order = {"report_question": 2, "medication_question": 3}
    return (
        min(risk_order.get(event.get("risk_level"), 5), type_order.get(event.get("event_type"), 5)),
        event.get("event_id", ""),
    )


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def parse_manual_review_decisions(queue_text: str) -> dict[str, str]:
    decisions: dict[str, str] = {}
    current_event_id: str | None = None
    for line in queue_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("### "):
            current_event_id = stripped.removeprefix("### ").strip()
            decisions[current_event_id] = "unchecked"
            continue
        if not current_event_id:
            continue
        lower = stripped.lower()
        if lower.startswith("- [x] "):
            decision = lower.removeprefix("- [x] ").strip()
            if decision in {"promote", "skip", "correction needed"}:
                decisions[current_event_id] = decision
    return decisions


def render_manual_review_queue(events: list[dict[str, Any]]) -> str:
    lines = [
        "# Manual Review Queue",
        "",
        f"Total items: {len(events)}",
        "",
        "Use this queue to decide whether draft imports can be promoted to official events.",
        "Do not treat imported AI summaries as medical facts without source review.",
        "",
    ]
    current_group = None
    for event in events:
        group = review_group(event)
        if group != current_group:
            current_group = group
            lines.extend(["", f"## {group}", ""])
        lines.extend(
            [
                f"### {event.get('event_id', 'unknown')}",
                "",
                f"- event_type: `{event.get('event_type', 'unknown')}`",
                f"- risk_level: `{event.get('risk_level', 'unknown')}`",
                f"- raw_source_path: `{event.get('raw_source_path', 'unknown')}`",
                f"- user_summary: {truncate(event.get('user_message_summary', ''))}",
                f"- assistant_summary: {truncate(event.get('assistant_response_summary', ''))}",
                "- decision:",
                "  - [ ] promote",
                "  - [ ] skip",
                "  - [ ] correction needed",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def review_group(event: dict[str, Any]) -> str:
    risk = event.get("risk_level")
    if risk == "red":
        return "Red Risk"
    if risk == "yellow":
        return "Yellow Risk"
    event_type = event.get("event_type")
    if event_type == "report_question":
        return "Report Questions"
    if event_type == "medication_question":
        return "Medication Questions"
    return "Other Manual Review"


def truncate(text: str, limit: int = 180) -> str:
    compact = " ".join(str(text).split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1] + "…"


def render_decisions_report(result: DecisionResult) -> str:
    return "\n".join(
        [
            "# Manual Review Decisions Report",
            "",
            f"- Promoted: {result.promoted}",
            f"- Skipped: {result.skipped}",
            f"- Corrections needed: {result.corrections_needed}",
            f"- Unchecked: {result.unchecked}",
            f"- Duplicates skipped: {result.duplicates}",
            "",
            "## Outputs",
            "",
            f"- Events: {result.events_path}",
            f"- Correction drafts: {result.correction_drafts_path}",
        ]
    ) + "\n"


def render_review_report(review: DraftReview, result: PromotionResult) -> str:
    lines = [
        "# Draft Review Report",
        "",
        f"- Total draft events: {review.total}",
        f"- Auto promotable: {review.auto_promotable}",
        f"- Manual review required: {review.manual_required}",
        f"- Promoted: {result.promoted}",
        f"- Duplicates skipped: {result.duplicates}",
        "",
        "## Event Types",
        "",
    ]
    for name, count in review.by_event_type.most_common():
        lines.append(f"- {name}: {count}")
    lines.extend(["", "## Risk Levels", ""])
    for name, count in review.by_risk_level.most_common():
        lines.append(f"- {name}: {count}")
    lines.extend(
        [
            "",
            "## Promotion Rule",
            "",
            "- Only green draft events without manual-review flags are promoted automatically.",
            "- Report, medication, yellow, and red events stay in draft until reviewed.",
        ]
    )
    return "\n".join(lines) + "\n"
