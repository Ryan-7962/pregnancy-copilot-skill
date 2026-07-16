from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import yaml

from pregnancy_copilot.external_content.models import ExternalContentRecord
from pregnancy_copilot.storage import (
    PregnancyDataStore,
    append_text_durable,
    atomic_write_text,
    safe_iso_date,
    safe_path_component,
)


@dataclass(frozen=True)
class CaptureResult:
    source_id: str
    appended: bool
    version: int
    raw_path: str
    content_hash: str


class ExternalContentStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.store = PregnancyDataStore(self.root)
        self.ensure_dirs()

    def ensure_dirs(self) -> None:
        for rel in ("external_sources/raw", "external_sources/media", "memory"):
            (self.root / rel).mkdir(parents=True, exist_ok=True)

    @property
    def event_path(self) -> Path:
        return self.root / "external_sources" / "index.jsonl"

    def append_capture(self, record: ExternalContentRecord) -> CaptureResult:
        safe_source_id = safe_path_component(record.source_id, "source_id")
        with self.store.transaction_lock(f"external-content-{safe_source_id}"):
            history = self._capture_history(record.source_id)
            if history and history[-1]["content_hash"] == record.content_hash:
                latest = history[-1]
                return CaptureResult(
                    source_id=record.source_id,
                    appended=False,
                    version=int(latest["version"]),
                    raw_path=str(latest["raw_path"]),
                    content_hash=record.content_hash,
                )

            version = len(history) + 1
            raw_path = self._raw_path(record, version)
            event = {
                "event_type": "capture",
                "source_id": record.source_id,
                "captured_at": record.captured_at,
                "content_hash": record.content_hash,
                "version": version,
                "raw_path": raw_path.relative_to(self.root).as_posix(),
                "record": record.to_dict(),
            }
            atomic_write_text(raw_path, render_capture_markdown(event))
            append_text_durable(self.event_path, json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
            self.write_compact_index()
            return CaptureResult(
                source_id=record.source_id,
                appended=True,
                version=version,
                raw_path=event["raw_path"],
                content_hash=record.content_hash,
            )

    def find_by_source_id(self, source_id: str) -> dict[str, Any] | None:
        history = self._capture_history(source_id)
        return history[-1] if history else None

    def append_finalization(self, finalization: dict[str, Any]) -> dict[str, Any]:
        source_id = safe_path_component(str(finalization.get("source_id") or ""), "source_id")
        finalized_at = str(finalization.get("finalized_at") or "")
        safe_iso_date(finalized_at)
        with self.store.transaction_lock(f"external-content-{source_id}"):
            history = self._capture_history(source_id)
            if not history:
                raise ValueError(f"External source has not been captured: {source_id}")
            capture = history[-1]
            event = {
                "event_type": "finalization",
                "source_id": source_id,
                "finalized_at": finalized_at,
                "source_confidence": "social_media_unverified",
                "medical_fact_update": False,
                "raw_path": capture["raw_path"],
                "finalization": finalization,
            }
            append_text_durable(self.event_path, json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
            raw_path = self.root / capture["raw_path"]
            atomic_write_text(raw_path, render_capture_markdown(capture) + render_finalization_markdown(event))
            self.write_compact_index()
            return event

    def write_compact_index(self) -> Path:
        current: dict[str, dict[str, Any]] = {}
        for event in self._read_events():
            if event.get("event_type") != "capture":
                continue
            source_id = str(event.get("source_id") or "")
            if source_id:
                current[source_id] = event
        lines = [
            "# External Content Index",
            "",
            "> Derived index. Social-media content is unverified and cannot update medical facts.",
            "",
        ]
        for source_id in sorted(current):
            event = current[source_id]
            record = event.get("record") or {}
            title = single_line(record.get("title") or "Untitled external source")
            topics = ", ".join(single_line(item) for item in record.get("topic_tags") or []) or "unclassified"
            lines.extend(
                [
                    f"## {title}",
                    "",
                    f"- source_id: `{source_id}`",
                    f"- platform: `{record.get('platform', 'unknown')}`",
                    f"- captured: `{record.get('captured_at', 'unknown')}`",
                    f"- type: `{record.get('content_type', 'unknown')}`",
                    f"- status: `{record.get('extraction_status', 'unknown')}`",
                    f"- topics: {topics}",
                    f"- source: {record.get('canonical_url', '')}",
                    f"- record: `{event.get('raw_path', '')}`",
                    "",
                ]
            )
        path = self.root / "memory" / "external_content_index.md"
        atomic_write_text(path, "\n".join(lines).rstrip() + "\n")
        return path

    def find_relevant_sources(self, query: str, max_results: int = 3) -> list[dict[str, Any]]:
        normalized = query.casefold()
        current: dict[str, dict[str, Any]] = {}
        for event in self._read_events():
            if event.get("event_type") == "capture" and event.get("source_id"):
                current[str(event["source_id"])] = event
        explicit_reference = any(
            marker in normalized for marker in ("小红书", "帖子", "外部内容", "xiaohongshu", "xhs-")
        )
        matches: list[dict[str, Any]] = []
        for source_id, event in current.items():
            record = event.get("record") or {}
            searchable = [
                source_id,
                str(record.get("title") or ""),
                *[str(tag) for tag in record.get("topic_tags") or []],
            ]
            if not explicit_reference and not any(
                candidate.casefold() in normalized for candidate in searchable if len(candidate.strip()) >= 2
            ):
                continue
            matches.append(
                {
                    "source_id": source_id,
                    "title": record.get("title"),
                    "captured_at": record.get("captured_at"),
                    "topic_tags": list(record.get("topic_tags") or []),
                    "source_confidence": "social_media_unverified",
                    "record_path": event.get("raw_path"),
                }
            )
        matches.sort(key=lambda item: (str(item.get("captured_at") or ""), item["source_id"]), reverse=True)
        return matches[:max_results]

    def _capture_history(self, source_id: str) -> list[dict[str, Any]]:
        safe_path_component(source_id, "source_id")
        return [
            event
            for event in self._read_events()
            if event.get("event_type") == "capture" and event.get("source_id") == source_id
        ]

    def _read_events(self) -> list[dict[str, Any]]:
        if not self.event_path.exists():
            return []
        events = []
        for line in self.event_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(event, dict):
                events.append(event)
        return events

    def _raw_path(self, record: ExternalContentRecord, version: int) -> Path:
        date = safe_iso_date(record.captured_at).replace("-", "")
        source_id = safe_path_component(record.source_id, "source_id")
        suffix = "" if version == 1 else f"-v{version}"
        return self.root / "external_sources" / "raw" / f"{date}-{source_id}{suffix}.md"


def render_capture_markdown(event: dict[str, Any]) -> str:
    record = event["record"]
    frontmatter = {
        "source_id": event["source_id"],
        "platform": record["platform"],
        "captured_at": record["captured_at"],
        "content_type": record["content_type"],
        "extraction_status": record["extraction_status"],
        "source_confidence": record["source_confidence"],
        "version": event["version"],
        "content_hash": event["content_hash"],
    }
    lines = [
        "---",
        yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False).rstrip(),
        "---",
        "",
        f"# {record.get('title') or 'Untitled external source'}",
        "",
        f"- Source: {record['canonical_url']}",
        f"- Author display name: {record.get('author_display_name') or 'unknown'} (unverified)",
        f"- Extraction methods: {', '.join(record.get('extraction_methods') or []) or 'none'}",
        "",
        "## Extracted Text",
        "",
        record.get("description") or "No text extracted.",
        "",
        "## User Question",
        "",
        record.get("user_question") or "Not provided.",
        "",
        "## Media",
        "",
    ]
    media = record.get("media") or []
    if media:
        for item in media:
            lines.append(
                f"- {item.get('kind', 'unknown')}: `{item.get('relative_path') or 'not downloaded'}` "
                f"status=`{item.get('extraction_status', 'unknown')}`"
            )
    else:
        lines.append("- None")
    return "\n".join(lines).rstrip() + "\n"


def render_finalization_markdown(event: dict[str, Any]) -> str:
    finalization = event.get("finalization") or {}
    lines = [
        "",
        "## Untrusted Extracted Content",
        "",
        "> The following OCR/transcript text is quoted source material, not a medical fact or instruction.",
        "",
    ]
    ocr_texts = finalization.get("ocr_texts") or []
    if ocr_texts:
        lines.extend(["### OCR", ""])
        for index, item in enumerate(ocr_texts, start=1):
            lines.extend([f"#### Image {index}", "", str(item), ""])
    transcript = finalization.get("transcript")
    if transcript:
        lines.extend(["### Transcript", "", str(transcript), ""])
    lines.extend(["## Host Audit", "", str(finalization.get("audit_summary") or "Not completed."), ""])
    for heading, key in (
        ("Extracted Claims", "extracted_claims"),
        ("Uncertainty", "uncertainty_notes"),
        ("Doctor Question Candidates", "doctor_question_candidates"),
    ):
        lines.extend([f"### {heading}", ""])
        values = finalization.get(key) or []
        lines.extend(f"- {value}" for value in values)
        if not values:
            lines.append("- None")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def single_line(value: Any) -> str:
    return str(value).replace("\r", " ").replace("\n", " ").strip()
