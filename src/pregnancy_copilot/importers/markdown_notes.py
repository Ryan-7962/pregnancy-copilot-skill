from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from pregnancy_copilot.importers.gemini_markdown import safe_filename, summarize
from pregnancy_copilot.storage import SCHEMA_VERSION
from pregnancy_copilot.triage import triage_message


@dataclass
class MarkdownNoteImportResult:
    source_count: int
    raw_files_written: int
    draft_events_path: Path
    report_path: Path


def import_markdown_notes_to_drafts(
    source_dir: str | Path,
    data_root: str | Path,
    source: str,
    raw_subdir: str,
    default_event_type: str,
    copy_to_reports: bool = False,
) -> MarkdownNoteImportResult:
    source_dir = Path(source_dir)
    root = Path(data_root)
    raw_dir = root / "inbox" / raw_subdir
    events_dir = root / "events"
    exports_dir = root / "exports"
    reports_dir = root / "reports"
    raw_dir.mkdir(parents=True, exist_ok=True)
    events_dir.mkdir(parents=True, exist_ok=True)
    exports_dir.mkdir(parents=True, exist_ok=True)
    if copy_to_reports:
        reports_dir.mkdir(parents=True, exist_ok=True)

    draft_events_path = events_dir / f"draft_{source}_events.jsonl"
    if draft_events_path.exists():
        draft_events_path.unlink()

    source_count = 0
    raw_files_written = 0
    with draft_events_path.open("a", encoding="utf-8") as handle:
        for source_path in sorted(source_dir.rglob("*")):
            if not source_path.is_file() or source_path.suffix.lower() not in {".md", ".markdown"}:
                continue
            source_count += 1
            text = source_path.read_text(encoding="utf-8", errors="replace")
            filename = f"{source_count:03d}-{safe_filename(source_path.name)}"
            raw_path = raw_dir / filename
            raw_path.write_text(text, encoding="utf-8")
            raw_files_written += 1
            if copy_to_reports:
                (reports_dir / filename).write_text(text, encoding="utf-8")
            event = build_note_draft_event(
                source=source,
                source_name=source_path.name,
                event_type=default_event_type,
                text=text,
                raw_source_path=raw_path.relative_to(root).as_posix(),
            )
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    report_path = exports_dir / f"{source}_import_report.md"
    report_path.write_text(render_note_import_report(source, source_count, raw_files_written, draft_events_path), encoding="utf-8")
    return MarkdownNoteImportResult(
        source_count=source_count,
        raw_files_written=raw_files_written,
        draft_events_path=draft_events_path,
        report_path=report_path,
    )


def build_note_draft_event(source: str, source_name: str, event_type: str, text: str, raw_source_path: str) -> dict:
    event_hash = hashlib.sha1(f"{source}:{source_name}:{text[:500]}".encode("utf-8")).hexdigest()[:12]
    triage = triage_message(text)
    risk_level = "yellow" if event_type == "prenatal_report" else triage.risk_level
    return {
        "schema_version": SCHEMA_VERSION,
        "event_id": f"{source}-{event_hash}",
        "event_type": event_type,
        "source": source,
        "source_name": source_name,
        "raw_source_path": raw_source_path,
        "user_message_summary": summarize(text),
        "assistant_response_summary": "",
        "risk_level": risk_level,
        "requires_manual_review": True,
        "import_status": "draft",
        "privacy_level": "private",
    }


def render_note_import_report(source: str, source_count: int, raw_files_written: int, draft_events_path: Path) -> str:
    return "\n".join(
        [
            f"# {source} Import Report",
            "",
            f"- Sources read: {source_count}",
            f"- Raw files written: {raw_files_written}",
            f"- Draft events: {draft_events_path}",
            "",
            "## Safety",
            "",
            "- These notes are imported as drafts.",
            "- Manual review is required before promotion to official events.",
        ]
    ) + "\n"
