import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

from pregnancy_copilot.context_builder import build_current_context
from pregnancy_copilot.data_init import initialize_data_dir
from pregnancy_copilot.medical_state import read_current_medical_state, record_medical_observation
from pregnancy_copilot.storage import PregnancyDataStore


def observation(value, measured_at, *, confidence="user_reported", status="unknown", source="evt-source"):
    return {
        "metric_key": "nt",
        "display_name": "NT",
        "value": value,
        "unit": "mm",
        "measured_at": measured_at,
        "status": status,
        "source_confidence": confidence,
        "source_event_id": source,
        "raw_source_path": f"inbox/{source}.md",
    }


def test_unknown_date_never_overrides_dated_current_observation(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    record_medical_observation(store, observation("1.8", "unknown", source="evt-undated"))
    state = record_medical_observation(
        store,
        observation("1.2", "2026-07-01", confidence="report_verified", status="normal", source="evt-dated"),
    )

    metric = state["metrics"]["nt"]
    assert metric["current"]["value"] == "1.2"
    assert metric["current"]["measured_at"] == "2026-07-01"
    assert metric["previous_values"] == []
    assert metric["candidates"][0]["value"] == "1.8"
    assert metric["candidates"][0]["candidate_reason"] == "missing_or_invalid_measured_at"


def test_low_confidence_candidate_does_not_replace_confirmed_current(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    record_medical_observation(
        store,
        observation("1.2", "2026-07-01", confidence="report_verified", status="normal", source="evt-verified"),
    )
    state = record_medical_observation(
        store,
        observation("1.7", "2026-07-08", confidence="ai_extracted", status="unknown", source="evt-ai"),
    )

    metric = state["metrics"]["nt"]
    assert metric["current"]["value"] == "1.2"
    assert metric["candidates"][0]["value"] == "1.7"
    assert metric["candidates"][0]["candidate_reason"] == "insufficient_source_confidence"


def test_new_dated_value_becomes_current_and_preserves_history(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    record_medical_observation(store, observation("1.4", "2026-06-20", source="evt-old"))
    state = record_medical_observation(store, observation("1.2", "2026-07-01", source="evt-new"))

    metric = state["metrics"]["nt"]
    assert metric["current"]["value"] == "1.2"
    assert metric["previous_values"][0]["value"] == "1.4"
    assert metric["previous_values"][0]["effective_status"] == "superseded"


def test_current_context_exposes_date_source_history_and_candidates(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    record_medical_observation(store, observation("1.4", "2026-06-20", source="evt-old"))
    record_medical_observation(store, observation("1.2", "2026-07-01", source="evt-new"))
    record_medical_observation(store, observation("1.8", "unknown", source="evt-undated"))

    content = build_current_context(store, as_of="2026-07-15").read_text(encoding="utf-8")

    assert "2026-07-01" in content
    assert "inbox/evt-new.md" in content
    assert "历史值：2026-06-20 1.4mm" in content
    assert "待确认候选" in content
    assert "unknown 1.8mm" in content


def test_supported_record_lifecycle_statuses_are_accepted(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)

    record_medical_observation(store, observation("1.3", "2026-07-02", status="confirmed"))
    record_medical_observation(store, observation("1.2", "2026-07-02", status="corrected", source="evt-corrected"))
    state = record_medical_observation(
        store,
        observation("1.3", "2026-07-02", status="superseded", source="evt-superseded"),
    )

    assert state["metrics"]["nt"]["current"]["value"] == "1.2"
    assert any(item["status"] == "superseded" for item in state["metrics"]["nt"]["candidates"])
    assert read_current_medical_state(store)["metrics"]["nt"]["current"]["status"] == "corrected"


def test_duplicate_medical_observation_is_idempotent(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    item = observation("1.2", "2026-07-01", source="evt-same")

    record_medical_observation(store, item)
    record_medical_observation(store, item)

    rows = (tmp_path / "events" / "medical_observations.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(rows) == 1


def test_concurrent_medical_observations_preserve_all_rows_and_latest_current(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    start = date(2026, 6, 1)

    def write(index: int) -> None:
        measured_at = (start + timedelta(days=index)).isoformat()
        record_medical_observation(store, observation(str(index), measured_at, source=f"evt-{index}"))

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(write, range(30)))

    rows = [
        json.loads(line)
        for line in (tmp_path / "events" / "medical_observations.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    state = read_current_medical_state(store)
    assert len(rows) == 30
    assert len({row["observation_id"] for row in rows}) == 30
    assert state["metrics"]["nt"]["current"]["value"] == "29"


def test_every_medical_observation_has_explicit_provenance(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    record_medical_observation(
        store,
        {
            "metric_key": "weight",
            "display_name": "体重",
            "value": 53.2,
            "unit": "kg",
            "measured_at": "2026-07-15",
            "status": "confirmed",
        },
    )
    record_medical_observation(store, observation("1.2", "2026-07-01", source="evt-report"))

    rows = [
        json.loads(line)
        for line in (tmp_path / "events" / "medical_observations.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    manual = next(row for row in rows if row["metric_key"] == "weight")
    report = next(row for row in rows if row["metric_key"] == "nt")
    assert manual["provenance"]["type"] == "manual_entry"
    assert manual["provenance"]["reference"].startswith("manual:")
    assert report["provenance"] == {
        "type": "raw_message",
        "reference": "inbox/evt-report.md",
        "source_event_id": "evt-report",
    }
