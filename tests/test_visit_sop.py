import json

import yaml

from pregnancy_copilot.daily_metrics import build_daily_metrics_index
from pregnancy_copilot.doctor_questions import add_question_candidates
from pregnancy_copilot.medical_state import record_medical_observation
from pregnancy_copilot.storage import PregnancyDataStore, SCHEMA_VERSION
from pregnancy_copilot.visit_sop import generate_post_visit_action_sop, generate_pre_visit_sop
from scripts.init_data_dir import initialize_data_dir


def base_event(**overrides):
    event = {
        "schema_version": SCHEMA_VERSION,
        "event_id": "evt-report-question",
        "event_type": "report_question",
        "mode": "pregnancy_qa",
        "timestamp": "2026-05-20T09:00:00+08:00",
        "gestational_age": "20w0d",
        "source": "host_agent",
        "raw_source_path": "inbox/raw_host_messages/2026-05-20.md",
        "user_message_summary": "B 超提示宫颈长度临界，要不要提前复查？",
        "risk_level": "yellow",
        "triage_required": True,
        "privacy_level": "summary",
        "doctor_question_candidates": ["宫颈长度临界，要不要提前复查？"],
    }
    event.update(overrides)
    return event


def test_generate_pre_visit_sop_uses_memory_indexes_without_private_events(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    store.append_event(base_event())
    store.append_event(
        base_event(
            event_id="evt-private",
            timestamp="2026-05-21T09:00:00+08:00",
            user_message_summary="private 记录不应出现",
            privacy_level="private",
        )
    )
    store.append_event(
        {
            "schema_version": SCHEMA_VERSION,
            "event_id": "evt-weight",
            "event_type": "pregnancy_log",
            "timestamp": "2026-05-21T08:00:00+08:00",
            "user_message_summary": "晨起体重 51.2kg，晚上睡眠 7 小时",
            "risk_level": "not_applicable",
            "triage_required": False,
            "privacy_level": "summary",
        }
    )
    add_question_candidates(store, base_event())
    record_medical_observation(
        store,
        {
            "observation_id": "obs-cervix-old",
            "metric_key": "cervical_length",
            "display_name": "宫颈管长度",
            "value": 29,
            "unit": "mm",
            "measured_at": "2026-05-08",
            "status": "watch",
            "interpretation": "需随访。",
            "source_event_id": "evt-old-report",
            "raw_source_path": "reports/2026-05-08-ultrasound.md",
        },
    )
    record_medical_observation(
        store,
        {
            "observation_id": "obs-cervix-new",
            "metric_key": "cervical_length",
            "display_name": "宫颈管长度",
            "value": 31,
            "unit": "mm",
            "measured_at": "2026-05-20",
            "status": "normal",
            "interpretation": "本次较前值改善。",
            "source_event_id": "evt-new-report",
            "raw_source_path": "reports/2026-05-20-ultrasound.md",
        },
    )
    build_daily_metrics_index(store)

    path = generate_pre_visit_sop(store, visit_date="2026-05-22", lookback_days=7)
    text = path.read_text(encoding="utf-8")

    assert "# 产检前问诊 SOP 2026-05-22" in text
    assert "宫颈管长度：31mm" in text
    assert "历史对比：2026-05-08 29mm" in text
    assert "最新体重：51.2kg" in text
    assert "宫颈长度临界，要不要提前复查？" in text
    assert "private 记录不应出现" not in text
    assert "不替代医生判断" in text


def test_generate_post_visit_action_sop_saves_raw_note_and_event(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    note = "医生说继续观察宫颈长度，下次两周后复查 B 超。每天记录腹痛和出血情况，不确定是否加药，等化验结果。"

    result = generate_post_visit_action_sop(
        store,
        visit_date="2026-05-22",
        doctor_note=note,
        source="clinic_visit",
    )

    note_text = result["note_path"].read_text(encoding="utf-8")
    sop_text = result["sop_path"].read_text(encoding="utf-8")
    events = [
        json.loads(line)
        for line in (tmp_path / "events" / "events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert "source: clinic_visit" in note_text
    assert "医生回复原文" in sop_text
    assert "继续观察宫颈长度" in sop_text
    assert "两周后复查 B 超" in sop_text
    assert "不确定是否加药" in sop_text
    assert events[0]["event_type"] == "doctor_visit_summary"
    assert events[0]["triage_required"] is False
    assert yaml.safe_load((tmp_path / "memory" / "profile.yaml").read_text(encoding="utf-8"))["schema_version"] == SCHEMA_VERSION
