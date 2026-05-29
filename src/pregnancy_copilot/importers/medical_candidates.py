from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from pregnancy_copilot.medical_state import record_medical_observation
from pregnancy_copilot.storage import PregnancyDataStore, SCHEMA_VERSION


@dataclass
class CandidateExtractionResult:
    candidate_count: int
    candidates_path: Path
    review_path: Path


@dataclass
class CandidatePromotionResult:
    promoted: int = 0
    skipped: int = 0
    pending: int = 0
    report_path: Path | None = None


NUMERIC_PATTERNS = [
    {
        "metric_key": "cervical_length",
        "display_name": "宫颈管长度",
        "unit": "mm",
        "patterns": [
            r"宫颈管?长度[：:\s]*(?P<value>\d+(?:\.\d+)?)\s*mm",
            r"宫颈[：:\s]*(?P<value>\d+(?:\.\d+)?)\s*mm",
        ],
    },
    {
        "metric_key": "amniotic_fluid_depth",
        "display_name": "羊水最大深度",
        "unit": "mm",
        "patterns": [
            r"羊水(?:最大)?深度[：:\s]*(?P<value>\d+(?:\.\d+)?)\s*mm",
            r"羊水最大深径[：:\s]*(?P<value>\d+(?:\.\d+)?)\s*mm",
        ],
    },
    {
        "metric_key": "thyroid_tsh",
        "display_name": "TSH",
        "unit": None,
        "patterns": [r"TSH[：:\s]*(?P<value>\d+(?:\.\d+)?)"],
    },
    {
        "metric_key": "bpd",
        "display_name": "双顶径 BPD",
        "unit": "mm",
        "patterns": [r"(?:BPD|双顶径)[：:\s]*(?P<value>\d+(?:\.\d+)?)\s*mm"],
    },
    {
        "metric_key": "hc",
        "display_name": "头围 HC",
        "unit": "mm",
        "patterns": [r"(?:HC|头围)[：:\s]*(?P<value>\d+(?:\.\d+)?)\s*mm"],
    },
    {
        "metric_key": "ac",
        "display_name": "腹围 AC",
        "unit": "mm",
        "patterns": [r"(?:AC|腹围)[：:\s]*(?P<value>\d+(?:\.\d+)?)\s*mm"],
    },
    {
        "metric_key": "fl",
        "display_name": "股骨长 FL",
        "unit": "mm",
        "patterns": [r"(?:FL|股骨(?:长)?)[：:\s]*(?P<value>\d+(?:\.\d+)?)\s*mm"],
    },
]

PLACENTA_PATTERNS = [
    r"(?:胎盘(?:位置)?[：:\s]*)?(?P<value>宫底\+?后壁|宫底后壁|宫底及后壁|后壁|前壁|胎盘低置|低置胎盘|下缘达宫颈内口)",
]


def extract_medical_observation_candidates(
    data_root: str | Path,
    draft_path: str | Path | None = None,
    candidates_path: str | Path | None = None,
    review_path: str | Path | None = None,
) -> CandidateExtractionResult:
    root = Path(data_root)
    draft_path = Path(draft_path) if draft_path else root / "events" / "draft_import_events.jsonl"
    candidates_path = Path(candidates_path) if candidates_path else root / "exports" / "medical_observation_candidates.jsonl"
    review_path = Path(review_path) if review_path else root / "exports" / "medical_observation_candidate_review.md"
    events = read_jsonl(draft_path)
    candidates = dedupe_candidates(candidate for event in events for candidate in candidates_from_event(event))
    candidates_path.parent.mkdir(parents=True, exist_ok=True)
    candidates_path.write_text(
        "".join(json.dumps(candidate, ensure_ascii=False, sort_keys=True) + "\n" for candidate in candidates),
        encoding="utf-8",
    )
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(render_candidate_review(candidates, candidates_path), encoding="utf-8")
    return CandidateExtractionResult(len(candidates), candidates_path, review_path)


def candidates_from_event(event: dict[str, Any]) -> list[dict[str, Any]]:
    if event.get("event_type") not in {"report_question", "medication_question", "symptom_qa"}:
        return []
    text = " ".join(str(event.get(key, "")) for key in ("user_message_summary", "assistant_response_summary"))
    candidates = []
    for spec in NUMERIC_PATTERNS:
        for pattern in spec["patterns"]:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                value = parse_number(match.group("value"))
                candidates.append(
                    build_candidate(
                        event=event,
                        metric_key=spec["metric_key"],
                        display_name=spec["display_name"],
                        value=value,
                        unit=spec["unit"],
                    )
                )
    for pattern in PLACENTA_PATTERNS:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            value = normalize_placenta_value(match.group("value"))
            if value:
                candidates.append(
                    build_candidate(
                        event=event,
                        metric_key="placenta_position",
                        display_name="胎盘位置",
                        value=value,
                        unit=None,
                    )
                )
    return candidates


def build_candidate(
    event: dict[str, Any],
    metric_key: str,
    display_name: str,
    value: Any,
    unit: str | None,
) -> dict[str, Any]:
    candidate = {
        "schema_version": SCHEMA_VERSION,
        "candidate_id": "",
        "source_event_id": event.get("event_id"),
        "source_event_type": event.get("event_type"),
        "source_risk_level": event.get("risk_level"),
        "raw_source_path": event.get("raw_source_path"),
        "turn_index": event.get("turn_index"),
        "metric_key": metric_key,
        "display_name": display_name,
        "value": value,
        "unit": unit,
        "measured_at": event.get("timestamp") or "unknown",
        "status": "unknown",
        "interpretation": "",
        "review_decision": "pending",
        "requires_human_confirmation": True,
        "extraction_method": "regex_from_import_summaries",
    }
    candidate["candidate_id"] = stable_candidate_id(candidate)
    return candidate


def promote_medical_observation_candidates(
    data_root: str | Path,
    candidates_path: str | Path | None = None,
) -> CandidatePromotionResult:
    root = Path(data_root)
    candidates_path = Path(candidates_path) if candidates_path else root / "exports" / "medical_observation_candidates.jsonl"
    result = CandidatePromotionResult(report_path=root / "exports" / "medical_observation_candidate_promotion_report.md")
    store = PregnancyDataStore(root)
    for candidate in read_jsonl(candidates_path):
        decision = str(candidate.get("review_decision", "pending")).lower()
        if decision == "promote":
            observation = candidate_to_observation(candidate)
            record_medical_observation(store, observation)
            result.promoted += 1
        elif decision == "skip":
            result.skipped += 1
        else:
            result.pending += 1
    assert result.report_path is not None
    result.report_path.parent.mkdir(parents=True, exist_ok=True)
    result.report_path.write_text(render_promotion_report(result), encoding="utf-8")
    return result


def candidate_to_observation(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "observation_id": "obs-" + candidate["candidate_id"].removeprefix("cand-"),
        "metric_key": candidate["metric_key"],
        "display_name": candidate["display_name"],
        "value": candidate["value"],
        "unit": candidate.get("unit"),
        "measured_at": candidate["measured_at"],
        "status": candidate.get("status") or "unknown",
        "interpretation": candidate.get("interpretation") or "",
        "source_event_id": candidate.get("source_event_id"),
        "raw_source_path": candidate.get("raw_source_path"),
    }


def render_candidate_review(candidates: list[dict[str, Any]], candidates_path: Path) -> str:
    lines = [
        "# Medical Observation Candidate Review",
        "",
        "> Candidates are not facts. Promote only after checking the private source locally.",
        "> This review file excludes raw user/assistant text.",
        "",
        f"- Candidates file: `{candidates_path}`",
        f"- Total candidates: {len(candidates)}",
        "",
        "| Candidate | Metric | Value | Source Event | Source | Decision |",
        "|---|---|---|---|---|---|",
    ]
    for candidate in candidates:
        value = candidate["value"]
        unit = candidate.get("unit") or ""
        lines.append(
            "| {candidate_id} | {metric} | {value}{unit} | {event_id} | {source} | {decision} |".format(
                candidate_id=escape_table_text(candidate["candidate_id"]),
                metric=escape_table_text(candidate["display_name"]),
                value=escape_table_text(value),
                unit=escape_table_text(unit),
                event_id=escape_table_text(candidate.get("source_event_id") or ""),
                source=escape_table_text(candidate.get("raw_source_path") or ""),
                decision=escape_table_text(candidate["review_decision"]),
            )
        )
    return "\n".join(lines) + "\n"


def render_promotion_report(result: CandidatePromotionResult) -> str:
    return "\n".join(
        [
            "# Medical Observation Candidate Promotion Report",
            "",
            f"- Promoted: {result.promoted}",
            f"- Skipped: {result.skipped}",
            f"- Pending: {result.pending}",
        ]
    ) + "\n"


def dedupe_candidates(candidates: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    result = []
    for candidate in candidates:
        key = (
            candidate.get("source_event_id"),
            candidate.get("metric_key"),
            str(candidate.get("value")),
            candidate.get("unit"),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(candidate)
    return result


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def parse_number(value: str) -> int | float:
    number = float(value)
    return int(number) if number.is_integer() else number


def normalize_placenta_value(value: str) -> str | None:
    compact = re.sub(r"\s+", "", value).strip("：:，。；;")
    if not compact or compact in {"胎盘", "位置"}:
        return None
    return compact


def stable_candidate_id(candidate: dict[str, Any]) -> str:
    seed = "|".join(
        str(candidate.get(key, ""))
        for key in ("source_event_id", "metric_key", "value", "unit", "raw_source_path")
    )
    return "cand-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def escape_table_text(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")
