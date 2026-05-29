from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile

from pregnancy_copilot.storage import SCHEMA_VERSION
from pregnancy_copilot.triage import triage_message


REPORT_KEYWORDS = ["B 超", "b 超", "报告", "检查", "数值", "NT", "无创", "唐筛", "胎盘", "宫颈", "羊水"]
MEDICATION_KEYWORDS = ["药", "剂量", "优甲乐", "叶酸", "DHA", "钙", "铁", "维生素"]
DIET_KEYWORDS = ["吃", "喝", "饮食", "咖啡", "茶", "水果", "海鲜", "蛋糕", "面包"]
PLAN_KEYWORDS = ["计划", "SOP", "清单", "产检", "问医生", "预约", "建卡"]


@dataclass
class ImportedTurn:
    source_name: str
    turn_index: int
    user_text: str
    assistant_text: str
    event_type: str
    risk_level: str
    requires_manual_review: bool


@dataclass
class ImportResult:
    source_count: int
    raw_files_written: int
    turn_count: int
    manual_review_count: int
    draft_events_path: Path
    report_path: Path


def extract_turns_from_markdown(markdown_text: str, source_name: str) -> list[ImportedTurn]:
    blocks = re.split(r"\n-{20,}\n", markdown_text)
    turns: list[ImportedTurn] = []
    for block in blocks:
        if "🤖 Assistant" not in block:
            continue
        user_part, assistant_part = block.split("🤖 Assistant", 1)
        user_text = clean_user_text(user_part)
        assistant_text = clean_assistant_text(assistant_part)
        if not user_text or not assistant_text:
            continue
        event_type = classify_event_type(user_text)
        triage = triage_message(user_text)
        turns.append(
            ImportedTurn(
                source_name=source_name,
                turn_index=len(turns) + 1,
                user_text=user_text,
                assistant_text=assistant_text,
                event_type=event_type,
                risk_level=triage.risk_level,
                requires_manual_review=requires_manual_review(user_text, event_type, triage.risk_level),
            )
        )
    return turns


def import_gemini_zip_to_drafts(zip_path: str | Path, data_root: str | Path) -> ImportResult:
    zip_path = Path(zip_path)
    root = Path(data_root)
    raw_dir = root / "inbox" / "raw_gemini_exports"
    raw_dir.mkdir(parents=True, exist_ok=True)
    (root / "events").mkdir(parents=True, exist_ok=True)
    (root / "exports").mkdir(parents=True, exist_ok=True)

    draft_events_path = root / "events" / "draft_import_events.jsonl"
    if draft_events_path.exists():
        draft_events_path.unlink()

    source_count = 0
    raw_files_written = 0
    turn_count = 0
    manual_review_count = 0

    with ZipFile(zip_path) as archive, draft_events_path.open("a", encoding="utf-8") as events_file:
        for info in archive.infolist():
            if info.is_dir() or not info.filename.lower().endswith((".md", ".markdown")):
                continue
            source_count += 1
            text = archive.read(info).decode("utf-8", errors="replace")
            raw_name = f"{source_count:03d}-{safe_filename(Path(info.filename).name)}"
            raw_path = raw_dir / raw_name
            raw_path.write_text(text, encoding="utf-8")
            raw_files_written += 1

            turns = extract_turns_from_markdown(text, source_name=info.filename)
            for turn in turns:
                event = turn_to_draft_event(turn, raw_path.relative_to(root).as_posix())
                events_file.write(json.dumps(event, ensure_ascii=False) + "\n")
                turn_count += 1
                if turn.requires_manual_review:
                    manual_review_count += 1

    report_path = root / "exports" / "gemini_import_report.md"
    report_path.write_text(
        render_import_report(source_count, raw_files_written, turn_count, manual_review_count, draft_events_path),
        encoding="utf-8",
    )

    return ImportResult(
        source_count=source_count,
        raw_files_written=raw_files_written,
        turn_count=turn_count,
        manual_review_count=manual_review_count,
        draft_events_path=draft_events_path,
        report_path=report_path,
    )


def turn_to_draft_event(turn: ImportedTurn, raw_source_path: str) -> dict:
    event_hash = hashlib.sha1(f"{turn.source_name}:{turn.turn_index}:{turn.user_text}".encode("utf-8")).hexdigest()[:12]
    return {
        "schema_version": SCHEMA_VERSION,
        "event_id": f"gemini-import-{event_hash}",
        "event_type": turn.event_type,
        "source": "gemini_import",
        "source_name": turn.source_name,
        "turn_index": turn.turn_index,
        "raw_source_path": raw_source_path,
        "user_message_summary": summarize(turn.user_text),
        "assistant_response_summary": summarize(turn.assistant_text),
        "risk_level": turn.risk_level,
        "requires_manual_review": turn.requires_manual_review,
        "import_status": "draft",
        "privacy_level": "private",
    }


def clean_user_text(text: str) -> str:
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(("---", "sourceFile:", "exportedBy:", "exportDate:", "# ", "http")):
            continue
        if re.fullmatch(r"[0-9a-fA-F-]{20,}", stripped):
            continue
        if stripped.endswith(".md") or stripped == "Gemini Chat":
            continue
        lines.append(stripped)
    return summarize(" ".join(lines), limit=1200)


def clean_assistant_text(text: str) -> str:
    return summarize(" ".join(line.strip() for line in text.splitlines() if line.strip()), limit=2000)


def classify_event_type(text: str) -> str:
    if any(keyword in text for keyword in REPORT_KEYWORDS):
        return "report_question"
    if any(keyword in text for keyword in MEDICATION_KEYWORDS):
        return "medication_question"
    if any(keyword in text for keyword in DIET_KEYWORDS):
        return "diet_question"
    if any(keyword in text for keyword in PLAN_KEYWORDS):
        return "care_plan_question"
    return "symptom_qa"


def requires_manual_review(text: str, event_type: str, risk_level: str) -> bool:
    return risk_level in {"yellow", "red"} or event_type in {"report_question", "medication_question"}


def safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-")
    return cleaned or "gemini-export.md"


def summarize(text: str, limit: int = 160) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1] + "…"


def render_import_report(
    source_count: int,
    raw_files_written: int,
    turn_count: int,
    manual_review_count: int,
    draft_events_path: Path,
) -> str:
    return "\n".join(
        [
            "# Gemini Import Report",
            "",
            f"- Sources read: {source_count}",
            f"- Raw files written: {raw_files_written}",
            f"- Turns extracted: {turn_count}",
            f"- Manual review required: {manual_review_count}",
            f"- Draft events: {draft_events_path}",
            "",
            "## Safety",
            "",
            "- Draft events are not authoritative medical facts.",
            "- Review report, medication, yellow, and red events before promotion to events.jsonl.",
            "- Raw imports stay under inbox/raw_gemini_exports and should not be committed.",
        ]
    )
