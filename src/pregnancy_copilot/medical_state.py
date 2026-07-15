from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .storage import PregnancyDataStore, SCHEMA_VERSION, append_text_durable, atomic_write_text


OBSERVATIONS_FILE = "medical_observations.jsonl"
CURRENT_STATE_PATH = "memory/current_medical_state.yaml"
TIMELINE_PATH = "memory/medical_observation_timeline.md"
SOURCE_CONFIDENCE_ORDER = {
    "unknown": 0,
    "ai_extracted": 1,
    "gemini_inferred": 1,
    "user_reported": 2,
    "clinician_reported": 3,
    "report_verified": 4,
}


def record_medical_observation(store: PregnancyDataStore, observation: dict[str, Any]) -> dict[str, Any]:
    store.ensure_dirs()
    normalized = normalize_observation(observation)
    with store.transaction_lock("medical-state"):
        append_medical_observation(store, normalized)
        return rebuild_current_medical_state(store)


def append_medical_observation(store: PregnancyDataStore, observation: dict[str, Any]) -> Path:
    store.validate_schema_version(observation)
    path = store.root / "events" / OBSERVATIONS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    observation_id = str(observation.get("observation_id") or "")
    if observation_id and medical_observation_exists(path, observation_id):
        return path
    append_text_durable(path, json.dumps(observation, ensure_ascii=False, sort_keys=True) + "\n")
    return path


def medical_observation_exists(path: Path, observation_id: str) -> bool:
    if not path.exists():
        return False
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if str(row.get("observation_id") or "") == observation_id:
            return True
    return False


def read_medical_observations(store: PregnancyDataStore) -> list[dict[str, Any]]:
    path = store.root / "events" / OBSERVATIONS_FILE
    if not path.exists():
        return []
    observations: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        observations.append(json.loads(line))
    return sorted(observations, key=observation_sort_key)


def read_current_medical_state(store: PregnancyDataStore) -> dict[str, Any]:
    path = store.root / CURRENT_STATE_PATH
    if not path.exists():
        return rebuild_current_medical_state(store)
    return yaml.safe_load(path.read_text(encoding="utf-8")) or empty_current_state()


def rebuild_current_medical_state(store: PregnancyDataStore) -> dict[str, Any]:
    store.ensure_dirs()
    observations = read_medical_observations(store)
    grouped: dict[str, list[dict[str, Any]]] = {}
    for observation in observations:
        grouped.setdefault(observation["metric_key"], []).append(observation)

    metrics: dict[str, Any] = {}
    open_watch_items: list[str] = []
    resolved_items: list[str] = []
    for metric_key, metric_observations in sorted(grouped.items()):
        eligible: list[dict[str, Any]] = []
        candidates: list[dict[str, Any]] = []
        for observation in metric_observations:
            reason = candidate_reason(observation)
            if reason:
                candidate = dict(observation)
                candidate["candidate_reason"] = reason
                candidates.append(candidate)
            else:
                eligible.append(observation)

        ordered = sorted(eligible, key=current_selection_key)
        current = dict(ordered[-1]) if ordered else {}
        previous_values = []
        for previous in ordered[:-1] if current else ordered:
            item = dict(previous)
            item["effective_status"] = "superseded"
            previous_values.append(item)
        metrics[metric_key] = {
            "display_name": current.get("display_name") or metric_observations[-1].get("display_name") or metric_key,
            "current": current,
            "previous_values": previous_values,
            "candidates": sorted(candidates, key=observation_sort_key),
        }
        status = current.get("status")
        if status == "watch":
            open_watch_items.append(format_current_metric_line(current))
        elif status == "resolved":
            resolved_items.append(format_current_metric_line(current))

    current_state = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "metrics": metrics,
        "open_watch_items": open_watch_items,
        "resolved_items": resolved_items,
        "principle": "Current decisions must prefer metrics.current over older previous_values; previous_values are historical and superseded unless explicitly reactivated by a newer observation.",
    }
    write_yaml(store.root / CURRENT_STATE_PATH, current_state)
    write_medical_observation_timeline(store, observations)
    return current_state


def normalize_observation(observation: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(observation)
    normalized.setdefault("schema_version", SCHEMA_VERSION)
    normalized.setdefault("recorded_at", datetime.now(timezone.utc).astimezone().isoformat())
    if not normalized.get("measured_at") and normalized.get("observed_at"):
        normalized["measured_at"] = normalized["observed_at"]
    if not normalized.get("observation_id"):
        normalized["observation_id"] = stable_observation_id(normalized)
    required = ["metric_key", "display_name", "value", "measured_at", "status"]
    missing = [key for key in required if normalized.get(key) in {None, ""}]
    if missing:
        raise ValueError(f"Missing medical observation fields: {', '.join(missing)}")
    if normalized["status"] not in {
        "normal", "watch", "resolved", "active", "unknown", "confirmed", "corrected", "superseded"
    }:
        raise ValueError(f"Unsupported observation status: {normalized['status']!r}")
    normalized.setdefault("source_confidence", "user_reported")
    if normalized["source_confidence"] not in SOURCE_CONFIDENCE_ORDER:
        raise ValueError(f"Unsupported source_confidence: {normalized['source_confidence']!r}")
    normalized.setdefault("interpretation", "")
    normalized.setdefault("source_event_id", None)
    normalized.setdefault("raw_source_path", None)
    normalized.setdefault("provenance", build_provenance(normalized))
    return normalized


def build_provenance(observation: dict[str, Any]) -> dict[str, Any]:
    raw_source_path = observation.get("raw_source_path")
    source_event_id = observation.get("source_event_id")
    if raw_source_path:
        return {
            "type": "raw_message",
            "reference": str(raw_source_path),
            "source_event_id": source_event_id,
        }
    if source_event_id:
        return {
            "type": "structured_event",
            "reference": str(source_event_id),
            "source_event_id": source_event_id,
        }
    return {
        "type": "manual_entry",
        "reference": f"manual:{observation['observation_id']}",
        "source_event_id": None,
    }


def stable_observation_id(observation: dict[str, Any]) -> str:
    seed = "|".join(
        str(observation.get(key, ""))
        for key in ["metric_key", "measured_at", "value", "source_event_id", "raw_source_path"]
    )
    import hashlib

    return "obs-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def observation_sort_key(observation: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(observation.get("measured_at", "")),
        str(observation.get("recorded_at", "")),
        str(observation.get("observation_id", "")),
    )


def current_selection_key(observation: dict[str, Any]) -> tuple[str, int, str, str]:
    return (
        str(observation.get("measured_at", ""))[:10],
        SOURCE_CONFIDENCE_ORDER.get(str(observation.get("source_confidence", "user_reported")), 0),
        str(observation.get("recorded_at", "")),
        str(observation.get("observation_id", "")),
    )


def candidate_reason(observation: dict[str, Any]) -> str | None:
    if observation.get("status") == "superseded":
        return "explicitly_superseded"
    if not valid_measured_at(observation.get("measured_at")):
        return "missing_or_invalid_measured_at"
    confidence = SOURCE_CONFIDENCE_ORDER.get(str(observation.get("source_confidence", "user_reported")), 0)
    if confidence < SOURCE_CONFIDENCE_ORDER["user_reported"]:
        return "insufficient_source_confidence"
    return None


def valid_measured_at(value: Any) -> bool:
    if not value:
        return False
    try:
        datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        try:
            datetime.strptime(str(value)[:10], "%Y-%m-%d")
        except ValueError:
            return False
    return True


def empty_current_state() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": None,
        "metrics": {},
        "open_watch_items": [],
        "resolved_items": [],
        "principle": "No medical observations recorded.",
    }


def format_current_metric_line(observation: dict[str, Any]) -> str:
    value = observation.get("value")
    unit = observation.get("unit")
    value_text = f"{value}{unit}" if unit else str(value)
    interpretation = observation.get("interpretation")
    line = f"{observation.get('display_name') or observation.get('metric_key')}：{value_text}"
    if interpretation:
        line += f"，{interpretation}"
    return line


def write_yaml(path: Path, payload: dict[str, Any]) -> None:
    atomic_write_text(path, yaml.safe_dump(payload, allow_unicode=True, sort_keys=False))


def write_medical_observation_timeline(store: PregnancyDataStore, observations: list[dict[str, Any]]) -> Path:
    path = store.root / TIMELINE_PATH
    lines = [
        "# Medical Observation Timeline",
        "",
        "> Generated from events/medical_observations.jsonl. Older values are history; current decisions should use current_medical_state.yaml.",
        "",
        "| Date | Metric | Value | Status | Source |",
        "|---|---|---|---|---|",
    ]
    for observation in observations:
        value = observation.get("value")
        unit = observation.get("unit")
        value_text = f"{value}{unit}" if unit else str(value)
        lines.append(
            "| {date} | {metric} | {value} | {status} | {source} |".format(
                date=escape_table_text(observation.get("measured_at", "unknown")),
                metric=escape_table_text(observation.get("display_name") or observation.get("metric_key", "")),
                value=escape_table_text(value_text),
                status=escape_table_text(observation.get("status", "")),
                source=escape_table_text(observation.get("raw_source_path") or observation.get("source_event_id") or ""),
            )
        )
    atomic_write_text(path, "\n".join(lines) + "\n")
    return path


def escape_table_text(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")
