from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from .storage import PregnancyDataStore, SCHEMA_VERSION


CONFIDENCE_LEVELS = {"report_verified", "user_reported", "gemini_inferred", "needs_review"}
PRIORITY_HEADINGS = {"高优先级": "high", "中优先级": "medium", "低优先级": "low"}


def import_obsidian_gemini_state(source_dir: str | Path, store: PregnancyDataStore) -> dict[str, Any]:
    ensure_initialized(store)
    source_dir = Path(source_dir)
    refined_dir = source_dir / "状态提炼"
    if not refined_dir.exists():
        raise FileNotFoundError(refined_dir)

    state_files = sorted(refined_dir.glob("*状态卡-*.md"))
    review_files = sorted(refined_dir.glob("*待核对清单-*.md"))
    confidence_entries: list[dict[str, Any]] = []
    review_items: list[dict[str, Any]] = []
    for path in state_files:
        confidence_entries.extend(extract_confidence_entries(path))
    for path in review_files:
        review_items.extend(extract_review_items(path))

    write_source_confidence(store, confidence_entries)
    write_open_review_items(store, review_items)
    write_gemini_state_summary(store, source_dir, state_files, review_files, confidence_entries, review_items)
    from .context_builder import build_current_context

    current_context = build_current_context(store)
    return {
        "source_files_read": len(state_files) + len(review_files),
        "raw_files_read": 0,
        "confidence_entries": len(confidence_entries),
        "review_items": len(review_items),
        "source_confidence": str(store.root / "memory" / "source_confidence.yaml"),
        "open_review_items": str(store.root / "memory" / "open_review_items.yaml"),
        "current_context": str(current_context),
    }


def ensure_initialized(store: PregnancyDataStore) -> None:
    if (store.root / "memory" / "profile.yaml").exists():
        store.ensure_dirs()
        return
    from .data_init import initialize_data_dir

    initialize_data_dir(store.root)


def extract_confidence_entries(path: Path) -> list[dict[str, Any]]:
    entries = []
    for row in iter_markdown_table_rows(path):
        confidence = row.get("可信度")
        if confidence not in CONFIDENCE_LEVELS:
            continue
        topic = row.get("主题") or row.get("项目")
        statement = row.get("当前记录") or row.get("线索") or row.get("状态")
        if not topic or not statement:
            continue
        entries.append(
            {
                "topic": topic,
                "statement": statement,
                "confidence": confidence,
                "source": row.get("来源", ""),
                "source_file": path.name,
            }
        )
    return entries


def extract_review_items(path: Path) -> list[dict[str, Any]]:
    items = []
    priority = "unknown"
    for line in path.read_text(encoding="utf-8").splitlines():
        heading = line.strip().lstrip("#").strip()
        if heading in PRIORITY_HEADINGS:
            priority = PRIORITY_HEADINGS[heading]
            continue
        row = parse_table_line(line)
        if not row or row.get("is_separator"):
            continue
        if row["cells"][0] == "项目":
            headers = row["cells"]
            continue
        if "headers" not in locals():
            continue
        data = dict(zip(headers, row["cells"]))
        item = data.get("项目")
        if not item:
            continue
        signal = data.get("当前线索") or data.get("冲突") or ""
        why_review = data.get("为什么要核对") or data.get("处理建议") or data.get("处理") or ""
        if not signal and not why_review and not data.get("来源"):
            continue
        items.append(
            {
                "priority": priority,
                "item": item,
                "signal": signal,
                "why_review": why_review,
                "source": data.get("来源", ""),
                "source_file": path.name,
                "status": "open",
            }
        )
    return items


def iter_markdown_table_rows(path: Path) -> list[dict[str, str]]:
    rows = []
    headers: list[str] | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        parsed = parse_table_line(line)
        if not parsed:
            headers = None
            continue
        if parsed.get("is_separator"):
            continue
        cells = parsed["cells"]
        if any(cell in {"主题", "项目"} for cell in cells):
            headers = cells
            continue
        if headers:
            rows.append(dict(zip(headers, cells)))
    return rows


def parse_table_line(line: str) -> dict[str, Any] | None:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return None
    cells = [cell.strip() for cell in stripped.strip("|").split("|")]
    is_separator = all(set(cell) <= {"-", ":"} for cell in cells)
    return {"cells": cells, "is_separator": is_separator}


def write_source_confidence(store: PregnancyDataStore, entries: list[dict[str, Any]]) -> None:
    store.ensure_dirs()
    counts = Counter(entry["confidence"] for entry in entries)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "source": "obsidian_gemini_state_refined",
        "summary": {level: counts.get(level, 0) for level in sorted(CONFIDENCE_LEVELS)},
        "entries": entries,
        "rules": [
            "report_verified can inform medical state only when backed by report or health archive.",
            "user_reported is a symptom or habit signal, not a confirmed medical fact.",
            "gemini_inferred is a discussion clue only.",
            "needs_review must not be used as current medical fact.",
        ],
    }
    (store.root / "memory" / "source_confidence.yaml").write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def write_open_review_items(store: PregnancyDataStore, items: list[dict[str, Any]]) -> None:
    store.ensure_dirs()
    counts = Counter(item["priority"] for item in items)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "source": "obsidian_gemini_state_refined",
        "summary": dict(counts),
        "items": items,
    }
    (store.root / "memory" / "open_review_items.yaml").write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def write_gemini_state_summary(
    store: PregnancyDataStore,
    source_dir: Path,
    state_files: list[Path],
    review_files: list[Path],
    confidence_entries: list[dict[str, Any]],
    review_items: list[dict[str, Any]],
) -> None:
    lines = [
        "# Gemini State Import Summary",
        "",
        "> 只读取状态提炼层；原始 Gemini 对话不进入当前记忆包。",
        "",
        f"- Source dir: {source_dir}",
        f"- State files read: {len(state_files)}",
        f"- Review files read: {len(review_files)}",
        f"- Confidence entries: {len(confidence_entries)}",
        f"- Open review items: {len(review_items)}",
        "",
        "## Rules",
        "",
        "- Gemini 历史只能作为线索，不能替代报告、化验单或医生结论。",
        "- `report_verified` 仍需保留 source path；`gemini_inferred` 不得写成医疗事实。",
        "- 需要核对的项目进入 open_review_items，等待用户或报告确认。",
    ]
    (store.root / "memory" / "gemini_state_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
