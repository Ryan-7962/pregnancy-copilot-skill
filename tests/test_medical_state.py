import json

import yaml

from scripts.init_data_dir import initialize_data_dir
from pregnancy_copilot.context_builder import build_current_context
from pregnancy_copilot.medical_state import (
    record_medical_observation,
    rebuild_current_medical_state,
    read_current_medical_state,
    read_medical_observations,
)
from pregnancy_copilot.storage import PregnancyDataStore


def test_later_observation_becomes_current_and_older_value_is_superseded(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)

    record_medical_observation(
        store,
        {
            "observation_id": "obs-placenta-0326",
            "metric_key": "placenta_position",
            "display_name": "胎盘位置",
            "value": "距宫颈内口 23mm",
            "measured_at": "2026-03-26",
            "status": "watch",
            "interpretation": "临界贴近，需复查。",
            "source_event_id": "evt-0326-us",
            "raw_source_path": "reports/2026-03-26-ultrasound.md",
        },
    )
    current = record_medical_observation(
        store,
        {
            "observation_id": "obs-placenta-0508",
            "metric_key": "placenta_position",
            "display_name": "胎盘位置",
            "value": "宫底后壁",
            "measured_at": "2026-05-08",
            "status": "resolved",
            "interpretation": "胎盘低置/临界状态已被本次 B 超刷新，当前不应继续按旧 23mm 判断。",
            "source_event_id": "evt-0508-us",
            "raw_source_path": "reports/2026-05-08-ultrasound.md",
        },
    )

    assert current["metrics"]["placenta_position"]["current"]["value"] == "宫底后壁"
    assert current["metrics"]["placenta_position"]["current"]["status"] == "resolved"
    previous = current["metrics"]["placenta_position"]["previous_values"]
    assert previous[0]["value"] == "距宫颈内口 23mm"
    assert previous[0]["effective_status"] == "superseded"
    assert "不应继续按旧 23mm 判断" in current["metrics"]["placenta_position"]["current"]["interpretation"]

    saved = yaml.safe_load((tmp_path / "memory" / "current_medical_state.yaml").read_text(encoding="utf-8"))
    assert saved["metrics"]["placenta_position"]["current"]["measured_at"] == "2026-05-08"
    observations = read_medical_observations(store)
    assert [item["observation_id"] for item in observations] == ["obs-placenta-0326", "obs-placenta-0508"]


def test_current_medical_state_keeps_unresolved_watch_items_current(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)

    record_medical_observation(
        store,
        {
            "observation_id": "obs-cervix-0508",
            "metric_key": "cervical_length",
            "display_name": "宫颈管长度",
            "value": 29,
            "unit": "mm",
            "measured_at": "2026-05-08",
            "status": "watch",
            "interpretation": "仍高于 25mm 阈值，但需要后续随访。",
            "source_event_id": "evt-0508-us",
            "raw_source_path": "reports/2026-05-08-ultrasound.md",
        },
    )

    current = read_current_medical_state(store)

    assert current["metrics"]["cervical_length"]["current"]["value"] == 29
    assert current["metrics"]["cervical_length"]["current"]["unit"] == "mm"
    assert current["metrics"]["cervical_length"]["current"]["status"] == "watch"
    assert current["open_watch_items"] == ["宫颈管长度：29mm，仍高于 25mm 阈值，但需要后续随访。"]


def test_observed_at_is_accepted_as_alias_for_measured_at(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)

    current = record_medical_observation(
        store,
        {
            "metric_key": "cervical_length",
            "display_name": "宫颈管长度",
            "value": 31,
            "unit": "mm",
            "observed_at": "2026-05-16",
            "status": "normal",
        },
    )

    observation = current["metrics"]["cervical_length"]["current"]
    assert observation["measured_at"] == "2026-05-16"
    assert observation["observed_at"] == "2026-05-16"


def test_same_metric_same_measured_date_uses_later_recorded_observation(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)

    record_medical_observation(
        store,
        {
            "observation_id": "obs-cervix-same-day-old",
            "metric_key": "cervical_length",
            "display_name": "宫颈管长度",
            "value": 29,
            "unit": "mm",
            "measured_at": "2026-05-16",
            "recorded_at": "2026-05-16T09:00:00+08:00",
            "status": "watch",
            "interpretation": "上午口述记录，待报告确认。",
        },
    )
    current = record_medical_observation(
        store,
        {
            "observation_id": "obs-cervix-same-day-new",
            "metric_key": "cervical_length",
            "display_name": "宫颈管长度",
            "value": 31,
            "unit": "mm",
            "measured_at": "2026-05-16",
            "recorded_at": "2026-05-16T18:00:00+08:00",
            "status": "normal",
            "interpretation": "晚间按报告补正，应作为同日最新值。",
        },
    )

    metric = current["metrics"]["cervical_length"]
    assert metric["current"]["value"] == 31
    assert metric["current"]["recorded_at"] == "2026-05-16T18:00:00+08:00"
    assert metric["previous_values"][0]["value"] == 29
    assert metric["previous_values"][0]["effective_status"] == "superseded"


def test_medical_observation_requires_measured_date_to_avoid_guessing(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)

    try:
        record_medical_observation(
            store,
            {
                "metric_key": "thyroid_tsh",
                "display_name": "TSH",
                "value": 1.2,
                "status": "normal",
            },
        )
    except ValueError as exc:
        assert "measured_at" in str(exc)
    else:
        raise AssertionError("Expected missing measured_at to be rejected")


def test_current_context_prefers_current_medical_state_over_old_events(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    store.append_event(
        {
            "schema_version": "0.1",
            "event_id": "evt-old-placenta",
            "event_type": "report_review",
            "timestamp": "2026-03-26T10:00:00+08:00",
            "gestational_age": "15w6d",
            "user_message_summary": "B 超提示胎盘距宫颈内口 23mm",
            "assistant_response_summary": "需要随访胎盘位置。",
            "risk_level": "yellow",
            "privacy_level": "summary",
        }
    )
    record_medical_observation(
        store,
        {
            "observation_id": "obs-placenta-0326",
            "metric_key": "placenta_position",
            "display_name": "胎盘位置",
            "value": "距宫颈内口 23mm",
            "measured_at": "2026-03-26",
            "status": "watch",
            "interpretation": "临界贴近，需复查。",
        },
    )
    record_medical_observation(
        store,
        {
            "observation_id": "obs-placenta-0508",
            "metric_key": "placenta_position",
            "display_name": "胎盘位置",
            "value": "宫底后壁",
            "measured_at": "2026-05-08",
            "status": "resolved",
            "interpretation": "旧 23mm 状态已被刷新，当前胎盘低置警报解除。",
        },
    )

    path = build_current_context(store)
    text = path.read_text(encoding="utf-8")

    assert "## 当前有效医学状态" in text
    assert "胎盘位置：宫底后壁" in text
    assert "旧值已被更新，不应作为当前判断依据" in text
    assert "距宫颈内口 23mm" in text


def test_rebuild_current_medical_state_is_deterministic_from_jsonl(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    path = tmp_path / "events" / "medical_observations.jsonl"
    path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "schema_version": "0.1",
                        "observation_id": "obs-old",
                        "metric_key": "thyroid_tsh",
                        "display_name": "TSH",
                        "value": 1.028,
                        "measured_at": "2026-02-09",
                        "status": "normal",
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "schema_version": "0.1",
                        "observation_id": "obs-new",
                        "metric_key": "thyroid_tsh",
                        "display_name": "TSH",
                        "value": 2.4,
                        "measured_at": "2026-05-12",
                        "status": "watch",
                        "interpretation": "需结合医生意见确认优甲乐剂量。",
                    },
                    ensure_ascii=False,
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    current = rebuild_current_medical_state(store)

    assert current["metrics"]["thyroid_tsh"]["current"]["value"] == 2.4
    assert current["metrics"]["thyroid_tsh"]["previous_values"][0]["value"] == 1.028
