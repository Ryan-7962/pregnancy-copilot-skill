from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .storage import PregnancyDataStore, SCHEMA_VERSION


OBSERVATIONS_FILE = "medical_observations.jsonl"
CURRENT_STATE_PATH = "memory/current_medical_state.yaml"
TIMELINE_PATH = "memory/medical_observation_timeline.md"


def record_medical_observation(store: PregnancyDataStore, observation: dict[str, Any]) -> dict[str, Any]:
    store.ensure_dirs()
    normalized = normalize_observation(observation)
    append_medical_observation(store, normalized)
    return rebuild_current_medical_state(store)


def append_medical_observation(store: PregnancyDataStore, observation: dict[str, Any]) -> Path:
    store.validate_schema_version(observation)
    path = store.root / "events" / OBSERVATIONS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(observation, ensure_ascii=False, sort_keys=True) + "\n")
    return path


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
        ordered = sorted(metric_observations, key=observation_sort_key)
        current = dict(ordered[-1])
        previous_values = []
        for previous in ordered[:-1]:
            item = dict(previous)
            item["effective_status"] = "superseded"
            previous_values.append(item)
        metrics[metric_key] = {
            "display_name": current.get("display_name") or metric_key,
            "current": current,
            "previous_values": previous_values,
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
    if normalized["status"] not in {"normal", "watch", "resolved", "active", "unknown"}:
        raise ValueError(f"Unsupported observation status: {normalized['status']!r}")
    normalized.setdefault("interpretation", "")
    normalized.setdefault("source_event_id", None)
    normalized.setdefault("raw_source_path", None)
    return normalized


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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")


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
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def escape_table_text(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")
