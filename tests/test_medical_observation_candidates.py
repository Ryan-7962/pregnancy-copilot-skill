import json

import yaml

from scripts.init_data_dir import initialize_data_dir
from pregnancy_copilot.importers.medical_candidates import (
    extract_medical_observation_candidates,
    promote_medical_observation_candidates,
)


def write_drafts(data_root, rows):
    path = data_root / "events" / "draft_import_events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")
    return path


def test_extract_medical_observation_candidates_without_raw_text_in_review(tmp_path):
    initialize_data_dir(tmp_path)
    draft_path = write_drafts(
        tmp_path,
        [
            {
                "event_id": "draft-report",
                "event_type": "report_question",
                "risk_level": "yellow",
                "requires_manual_review": True,
                "raw_source_path": "inbox/raw_gemini_exports/source.md",
                "turn_index": 8,
                "user_message_summary": "private raw: 宫颈管长度 31mm，羊水最大深度 45mm，胎盘后壁。",
                "assistant_response_summary": "private answer with BPD 55mm and TSH 1.028。",
            }
        ],
    )

    result = extract_medical_observation_candidates(tmp_path, draft_path=draft_path)

    assert result.candidate_count == 5
    rows = [json.loads(line) for line in result.candidates_path.read_text(encoding="utf-8").splitlines()]
    metrics = {row["metric_key"]: row for row in rows}
    assert metrics["cervical_length"]["value"] == 31
    assert metrics["amniotic_fluid_depth"]["value"] == 45
    assert metrics["placenta_position"]["value"] == "后壁"
    assert metrics["bpd"]["value"] == 55
    assert metrics["thyroid_tsh"]["value"] == 1.028
    assert all(row["review_decision"] == "pending" for row in rows)
    assert all(row["requires_human_confirmation"] is True for row in rows)

    review = result.review_path.read_text(encoding="utf-8")
    assert "private raw" not in review
    assert "private answer" not in review
    assert "draft-report" in review
    assert "宫颈管长度" in review


def test_extract_medical_observation_candidates_rejects_loose_placenta_phrases(tmp_path):
    initialize_data_dir(tmp_path)
    draft_path = write_drafts(
        tmp_path,
        [
            {
                "event_id": "draft-loose-placenta",
                "event_type": "report_question",
                "risk_level": "yellow",
                "requires_manual_review": True,
                "raw_source_path": "inbox/raw_gemini_exports/source.md",
                "user_message_summary": "胎盘上移之前需要注意休息，不是一个明确报告值。",
                "assistant_response_summary": "胎盘位置 后壁 是明确报告值。",
            }
        ],
    )

    result = extract_medical_observation_candidates(tmp_path, draft_path=draft_path)
    rows = [json.loads(line) for line in result.candidates_path.read_text(encoding="utf-8").splitlines()]

    assert len(rows) == 1
    assert rows[0]["metric_key"] == "placenta_position"
    assert rows[0]["value"] == "后壁"
    review = result.review_path.read_text(encoding="utf-8")
    assert "上移之前" not in review


def test_promote_reviewed_candidates_updates_current_medical_state(tmp_path):
    initialize_data_dir(tmp_path)
    candidates_path = tmp_path / "exports" / "medical_observation_candidates.jsonl"
    candidates_path.parent.mkdir(parents=True, exist_ok=True)
    candidate = {
        "schema_version": "0.1",
        "candidate_id": "cand-cervix-new",
        "source_event_id": "draft-report",
        "raw_source_path": "inbox/raw_gemini_exports/source.md",
        "metric_key": "cervical_length",
        "display_name": "宫颈管长度",
        "value": 31,
        "unit": "mm",
        "measured_at": "2026-05-16",
        "status": "normal",
        "interpretation": "本次复查值。",
        "review_decision": "promote",
    }
    pending = {**candidate, "candidate_id": "cand-pending", "value": 29, "review_decision": "pending"}
    candidates_path.write_text(
        json.dumps(candidate, ensure_ascii=False) + "\n" + json.dumps(pending, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    result = promote_medical_observation_candidates(tmp_path, candidates_path=candidates_path)

    assert result.promoted == 1
    assert result.pending == 1
    state = yaml.safe_load((tmp_path / "memory" / "current_medical_state.yaml").read_text(encoding="utf-8"))
    assert state["metrics"]["cervical_length"]["current"]["value"] == 31
    observations = (tmp_path / "events" / "medical_observations.jsonl").read_text(encoding="utf-8")
    assert "cand-pending" not in observations
