import pytest

from scripts.init_data_dir import initialize_data_dir
from pregnancy_copilot.doctor_questions import (
    add_question_candidates,
    read_doctor_questions,
    render_doctor_questions_markdown,
    update_question_status,
)
from pregnancy_copilot.storage import PregnancyDataStore


def event_record(**overrides):
    event = {
        "schema_version": "0.1",
        "event_id": "evt-report",
        "event_type": "report_question",
        "mode": "pregnancy_qa",
        "timestamp": "2026-05-05T09:00:00+08:00",
        "gestational_age": "20w0d",
        "source": "feishu",
        "raw_source_path": "inbox/raw_feishu_messages/2026-05-05.md",
        "user_message_summary": "B 超报告是否需要复查？",
        "risk_level": "yellow",
        "doctor_question_candidates": ["B 超报告是否需要复查？"],
    }
    event.update(overrides)
    return event


def test_add_question_candidates_dedupes_and_renders_active_markdown(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)

    added = add_question_candidates(store, event_record())
    add_question_candidates(store, event_record(event_id="evt-repeat"))
    markdown_path = render_doctor_questions_markdown(store)

    records = read_doctor_questions(store)
    assert len(added) == 1
    assert len(records) == 1
    assert records[0]["status"] == "open"
    assert records[0]["risk_level"] == "yellow"
    assert "B 超报告是否需要复查" in markdown_path.read_text(encoding="utf-8")


def test_explicit_doctor_question_mode_uses_message_summary(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)

    added = add_question_candidates(
        store,
        event_record(
            event_id="evt-explicit",
            mode="doctor_questions",
            user_message_summary="下次产检要不要问宫颈长度？",
            doctor_question_candidates=[],
        ),
    )

    assert added[0]["question"] == "下次产检要不要问宫颈长度？"


def test_update_question_status_rewrites_lifecycle_record(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    question = add_question_candidates(store, event_record())[0]

    updated = update_question_status(
        store,
        question["question_id"],
        "answered",
        answer_summary="医生说按原计划复查。",
        updated_at="2026-05-06T10:00:00+08:00",
    )

    assert updated["status"] == "answered"
    assert updated["answer_summary"] == "医生说按原计划复查。"
    assert read_doctor_questions(store, statuses={"open"}) == []


def test_update_question_status_rejects_unknown_status(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    question = add_question_candidates(store, event_record())[0]

    with pytest.raises(ValueError):
        update_question_status(store, question["question_id"], "done")
