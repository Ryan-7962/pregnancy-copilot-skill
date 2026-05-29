from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from pregnancy_copilot.context_builder import build_current_context
from pregnancy_copilot.data_init import initialize_data_dir
from pregnancy_copilot.medical_state import format_current_metric_line, record_medical_observation
from pregnancy_copilot.storage import PregnancyDataStore


def run_record_medical_observation(
    data_root: str | Path,
    observation: dict[str, Any] | None = None,
    observation_json: str | None = None,
    observation_path: str | Path | None = None,
) -> dict[str, Any]:
    payload = load_observation_payload(
        observation=observation,
        observation_json=observation_json,
        observation_path=observation_path,
    )
    initialize_data_dir(data_root)
    store = PregnancyDataStore(data_root)
    state = record_medical_observation(store, payload)
    context_path = build_current_context(store)
    metric_key = payload["metric_key"]
    current = state["metrics"][metric_key]["current"]
    return {
        "ok": True,
        "observation_id": current["observation_id"],
        "metric_key": metric_key,
        "display_name": current.get("display_name") or metric_key,
        "current_value": format_value(current),
        "current_line": format_current_metric_line(current),
        "status": current["status"],
        "current_medical_state": str((Path(data_root) / "memory" / "current_medical_state.yaml").as_posix()),
        "medical_observations": str((Path(data_root) / "events" / "medical_observations.jsonl").as_posix()),
        "current_context": str(context_path.as_posix()),
    }


def load_observation_payload(
    observation: dict[str, Any] | None = None,
    observation_json: str | None = None,
    observation_path: str | Path | None = None,
) -> dict[str, Any]:
    provided = [value is not None for value in [observation, observation_json, observation_path]].count(True)
    if provided != 1:
        raise ValueError("Provide exactly one of observation, observation_json, or observation_path.")
    if observation is not None:
        return observation
    if observation_json is not None:
        return json.loads(observation_json)
    assert observation_path is not None
    return json.loads(Path(observation_path).read_text(encoding="utf-8"))


def format_value(observation: dict[str, Any]) -> str:
    value = observation.get("value")
    unit = observation.get("unit")
    return f"{value}{unit}" if unit else str(value)


def main() -> None:
    parser = argparse.ArgumentParser(description="Record a structured medical observation and refresh current medical state.")
    parser.add_argument("--data-root", required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--json", help="Observation JSON string.")
    source.add_argument("--file", help="Path to observation JSON file.")
    args = parser.parse_args()

    result = run_record_medical_observation(
        data_root=args.data_root,
        observation_json=args.json,
        observation_path=args.file,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
