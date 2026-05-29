import json

import pytest
import yaml

from scripts.record_medical_observation import run_record_medical_observation


def test_record_medical_observation_script_updates_current_state_and_context(tmp_path):
    old_observation = {
        "metric_key": "placenta_position",
        "display_name": "胎盘位置",
        "value": "距宫颈内口 23mm",
        "measured_at": "2026-03-26",
        "status": "watch",
        "interpretation": "临界贴近，需复查。",
    }
    new_observation = {
        "metric_key": "placenta_position",
        "display_name": "胎盘位置",
        "value": "宫底后壁",
        "measured_at": "2026-05-08",
        "status": "resolved",
        "interpretation": "旧 23mm 状态已被刷新，当前胎盘低置警报解除。",
    }

    run_record_medical_observation(tmp_path, old_observation)
    result = run_record_medical_observation(tmp_path, new_observation)

    assert result["ok"] is True
    assert result["metric_key"] == "placenta_position"
    assert result["current_value"] == "宫底后壁"
    assert result["current_medical_state"].endswith("memory/current_medical_state.yaml")
    assert result["current_context"].endswith("memory/current_context.md")
    state = yaml.safe_load((tmp_path / "memory" / "current_medical_state.yaml").read_text(encoding="utf-8"))
    assert state["metrics"]["placenta_position"]["current"]["value"] == "宫底后壁"
    context = (tmp_path / "memory" / "current_context.md").read_text(encoding="utf-8")
    assert "胎盘位置：宫底后壁" in context


def test_record_medical_observation_script_accepts_json_file(tmp_path):
    observation_path = tmp_path / "obs.json"
    observation_path.write_text(
        json.dumps(
            {
                "metric_key": "cervical_length",
                "display_name": "宫颈管长度",
                "value": 29,
                "unit": "mm",
                "measured_at": "2026-05-08",
                "status": "watch",
                "interpretation": "需随访。",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = run_record_medical_observation(tmp_path, observation_path=observation_path)

    assert result["ok"] is True
    assert result["metric_key"] == "cervical_length"
    assert result["current_value"] == "29mm"


def test_record_medical_observation_script_rejects_missing_payload(tmp_path):
    with pytest.raises(ValueError):
        run_record_medical_observation(tmp_path)
