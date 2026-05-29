from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ImportCategoryAnalysis:
    total: int = 0
    manual_required: int = 0
    auto_promotable: int = 0
    by_event_type: Counter = field(default_factory=Counter)
    by_risk_level: Counter = field(default_factory=Counter)
    manual_by_event_type: Counter = field(default_factory=Counter)
    manual_by_risk_level: Counter = field(default_factory=Counter)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "manual_required": self.manual_required,
            "auto_promotable": self.auto_promotable,
            "by_event_type": dict(self.by_event_type.most_common()),
            "by_risk_level": dict(self.by_risk_level.most_common()),
            "manual_by_event_type": dict(self.manual_by_event_type.most_common()),
            "manual_by_risk_level": dict(self.manual_by_risk_level.most_common()),
        }


@dataclass
class ReviewLaneAnalysis:
    total_manual: int = 0
    by_lane: Counter = field(default_factory=Counter)
    by_medical_signal: Counter = field(default_factory=Counter)
    lane_examples: dict[str, list[str]] = field(default_factory=dict)
    signal_examples: dict[str, list[str]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_manual": self.total_manual,
            "by_lane": dict(self.by_lane.most_common()),
            "by_medical_signal": dict(self.by_medical_signal.most_common()),
            "lane_examples": self.lane_examples,
            "signal_examples": self.signal_examples,
        }


MEDICAL_SIGNAL_BUCKETS = {
    "cervical_length": ["宫颈", "宫颈管", "宫颈长度", "宫颈管长度"],
    "placenta_position": ["胎盘", "低置", "前置"],
    "amniotic_fluid": ["羊水", "最大深度", "AFI"],
    "fetal_growth": ["BPD", "双顶径", "HC", "头围", "AC", "腹围", "FL", "股骨"],
    "thyroid": ["TSH", "甲状腺", "优甲乐"],
    "glucose": ["血糖", "糖耐", "OGTT", "尿糖"],
    "infection": ["白细胞", "尿检", "尿常规", "白带", "霉菌", "感染"],
    "tumor_marker": ["AFP", "CA19-9", "肿瘤标志物"],
    "medication_or_supplement": ["用药", "吃药", "剂量", "钙片", "DHA", "叶酸", "铁剂"],
}


def analyze_import_drafts(draft_path: str | Path) -> ImportCategoryAnalysis:
    analysis = ImportCategoryAnalysis()
    for event in read_jsonl(Path(draft_path)):
        analysis.total += 1
        event_type = event.get("event_type", "unknown")
        risk_level = event.get("risk_level", "unknown")
        analysis.by_event_type[event_type] += 1
        analysis.by_risk_level[risk_level] += 1
        if event.get("requires_manual_review"):
            analysis.manual_required += 1
            analysis.manual_by_event_type[event_type] += 1
            analysis.manual_by_risk_level[risk_level] += 1
        else:
            analysis.auto_promotable += 1
    return analysis


def analyze_review_lanes(draft_path: str | Path, examples_per_group: int = 5) -> ReviewLaneAnalysis:
    analysis = ReviewLaneAnalysis()
    for event in read_jsonl(Path(draft_path)):
        if not event.get("requires_manual_review"):
            continue
        analysis.total_manual += 1
        lane = classify_review_lane(event)
        analysis.by_lane[lane] += 1
        append_example(analysis.lane_examples, lane, event, examples_per_group)
        for signal in detect_medical_signal_buckets(event):
            analysis.by_medical_signal[signal] += 1
            append_example(analysis.signal_examples, signal, event, examples_per_group)
    return analysis


def write_import_category_report(draft_path: str | Path, output_path: str | Path) -> Path:
    draft_path = Path(draft_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    analysis = analyze_import_drafts(draft_path)
    output_path.write_text(render_import_category_report(analysis, draft_path), encoding="utf-8")
    return output_path


def write_review_sample_report(
    draft_path: str | Path,
    output_path: str | Path,
    per_bucket: int = 3,
) -> Path:
    draft_path = Path(draft_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    manual_events = [
        event
        for event in read_jsonl(draft_path)
        if event.get("requires_manual_review")
    ]
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for event in manual_events:
        key = (str(event.get("event_type", "unknown")), str(event.get("risk_level", "unknown")))
        buckets.setdefault(key, []).append(event)
    output_path.write_text(
        render_review_sample_report(buckets=buckets, draft_path=draft_path, per_bucket=per_bucket),
        encoding="utf-8",
    )
    return output_path


def write_review_lane_report(
    draft_path: str | Path,
    output_path: str | Path,
    examples_per_group: int = 5,
) -> Path:
    draft_path = Path(draft_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    analysis = analyze_review_lanes(draft_path, examples_per_group=examples_per_group)
    output_path.write_text(render_review_lane_report(analysis, draft_path), encoding="utf-8")
    return output_path


def render_import_category_report(analysis: ImportCategoryAnalysis, draft_path: Path) -> str:
    lines = [
        "# Import Category Report",
        "",
        "> Aggregated counts only. This report intentionally excludes raw user text and assistant text.",
        "",
        f"- Draft source: `{draft_path}`",
        f"- Total draft events: {analysis.total}",
        f"- Auto-promotable candidates: {analysis.auto_promotable}",
        f"- Manual review required: {analysis.manual_required}",
        "",
        "## Event Types",
        "",
    ]
    append_counter(lines, analysis.by_event_type)
    lines.extend(["", "## Risk Levels", ""])
    append_counter(lines, analysis.by_risk_level)
    lines.extend(["", "## Manual Review By Event Type", ""])
    append_counter(lines, analysis.manual_by_event_type)
    lines.extend(["", "## Manual Review By Risk Level", ""])
    append_counter(lines, analysis.manual_by_risk_level)
    lines.extend(
        [
            "",
            "## Test Coverage Implications",
            "",
            "- Synthetic public cases should cover each major event type.",
            "- Synthetic public cases should cover green, yellow, and red outcomes.",
            "- Memory tests should verify that imported drafts do not become current medical facts until reviewed.",
            "- Context tests should verify that large imports are summarized as patterns, not expanded as raw history.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_review_sample_report(
    buckets: dict[tuple[str, str], list[dict[str, Any]]],
    draft_path: Path,
    per_bucket: int,
) -> str:
    lines = [
        "# Manual Review Sample Report",
        "",
        "> Local review aid. This report lists event IDs, categories, risk levels, and raw source paths only.",
        "> It intentionally excludes user and assistant summaries to avoid spreading private conversation text.",
        "",
        f"- Draft source: `{draft_path}`",
        f"- Per bucket: {per_bucket}",
        "",
    ]
    for key in sorted(buckets, key=lambda item: (risk_sort(item[1]), item[0])):
        event_type, risk_level = key
        events = sorted(buckets[key], key=lambda event: str(event.get("event_id", "")))
        lines.extend(["", f"## {event_type} / {risk_level}", ""])
        lines.append(f"- total: {len(events)}")
        for event in events[:per_bucket]:
            lines.append(
                "- `{event_id}` source=`{source}` turn=`{turn}`".format(
                    event_id=event.get("event_id", "unknown"),
                    source=event.get("raw_source_path", "unknown"),
                    turn=event.get("turn_index", "unknown"),
                )
            )
    return "\n".join(lines).strip() + "\n"


def render_review_lane_report(analysis: ReviewLaneAnalysis, draft_path: Path) -> str:
    lines = [
        "# Manual Review Lane Report",
        "",
        "> Aggregated routing aid only. This report intentionally excludes raw user text, assistant text, and summaries.",
        "",
        f"- Draft source: `{draft_path}`",
        f"- Total manual-review events: {analysis.total_manual}",
        "",
        "## Review Lanes",
        "",
    ]
    append_counter(lines, analysis.by_lane)
    lines.extend(["", "## Medical Signal Buckets", ""])
    append_counter(lines, analysis.by_medical_signal)
    lines.extend(["", "## Lane Examples", ""])
    append_examples(lines, analysis.lane_examples)
    lines.extend(["", "## Signal Examples", ""])
    append_examples(lines, analysis.signal_examples)
    lines.extend(
        [
            "",
            "## Suggested Handling",
            "",
            "- `structured_medical_candidate`: inspect source locally and extract confirmed report/lab values into `medical_observations.jsonl`.",
            "- `medication_review_candidate`: keep for host LLM context or clinician question list; do not auto-convert to medication orders.",
            "- `urgent_or_yellow_risk_review`: preserve as reviewed clinical history only after human confirmation.",
            "- `historical_pattern_review`: usually stays as historical Q&A pattern unless it updates current facts.",
        ]
    )
    return "\n".join(lines) + "\n"


def classify_review_lane(event: dict[str, Any]) -> str:
    event_type = event.get("event_type")
    risk_level = event.get("risk_level")
    signals = set(detect_medical_signal_buckets(event))
    if event_type == "report_question" or signals & {
        "cervical_length",
        "placenta_position",
        "amniotic_fluid",
        "fetal_growth",
        "thyroid",
        "glucose",
        "infection",
        "tumor_marker",
    }:
        return "structured_medical_candidate"
    if event_type == "medication_question" or "medication_or_supplement" in signals:
        return "medication_review_candidate"
    if risk_level in {"red", "yellow"}:
        return "urgent_or_yellow_risk_review"
    return "historical_pattern_review"


def detect_medical_signal_buckets(event: dict[str, Any]) -> list[str]:
    text = " ".join(
        str(event.get(key, ""))
        for key in ("event_type", "user_message_summary", "assistant_response_summary")
    )
    signals = []
    for bucket, keywords in MEDICAL_SIGNAL_BUCKETS.items():
        if any(re.search(re.escape(keyword), text, flags=re.IGNORECASE) for keyword in keywords):
            signals.append(bucket)
    return signals


def append_counter(lines: list[str], counter: Counter) -> None:
    if not counter:
        lines.append("- none: 0")
        return
    for name, count in counter.most_common():
        lines.append(f"- {name}: {count}")


def append_example(container: dict[str, list[str]], key: str, event: dict[str, Any], limit: int) -> None:
    examples = container.setdefault(key, [])
    if len(examples) < limit:
        examples.append(str(event.get("event_id", "unknown")))


def append_examples(lines: list[str], examples_by_group: dict[str, list[str]]) -> None:
    if not examples_by_group:
        lines.append("- none")
        return
    for name in sorted(examples_by_group):
        ids = ", ".join(f"`{event_id}`" for event_id in examples_by_group[name])
        lines.append(f"- {name}: {ids}")


def risk_sort(risk_level: str) -> int:
    return {"red": 0, "yellow": 1, "green": 2}.get(risk_level, 9)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
