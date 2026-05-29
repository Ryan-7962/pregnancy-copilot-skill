import json

from scripts.init_data_dir import initialize_data_dir
from pregnancy_copilot.importers.draft_review import (
    apply_manual_review_decisions,
    generate_manual_review_queue,
    promote_import_drafts,
    review_import_drafts,
)


def write_drafts(data_root, rows):
    path = data_root / "events" / "draft_import_events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )
    return path


def base_event(event_id, event_type, risk_level="green", manual=False):
    return {
        "schema_version": "0.1",
        "event_id": event_id,
        "event_type": event_type,
        "source": "gemini_import",
        "raw_source_path": "inbox/raw_gemini_exports/sample.md",
        "user_message_summary": "summary",
        "assistant_response_summary": "response",
        "risk_level": risk_level,
        "requires_manual_review": manual,
        "import_status": "draft",
        "privacy_level": "private",
    }


def test_review_import_drafts_classifies_auto_promotable_and_manual_items(tmp_path):
    initialize_data_dir(tmp_path)
    draft_path = write_drafts(
        tmp_path,
        [
            base_event("draft-green-diet", "diet_question"),
            base_event("draft-report", "report_question", manual=True),
            base_event("draft-red", "symptom_qa", risk_level="red", manual=True),
        ],
    )

    review = review_import_drafts(draft_path)

    assert review.total == 3
    assert review.auto_promotable == 1
    assert review.manual_required == 2
    assert review.by_event_type["diet_question"] == 1
    assert review.by_risk_level["red"] == 1


def test_promote_import_drafts_appends_only_safe_low_risk_events(tmp_path):
    initialize_data_dir(tmp_path)
    draft_path = write_drafts(
        tmp_path,
        [
            base_event("draft-green-diet", "diet_question"),
            base_event("draft-green-symptom", "symptom_qa"),
            base_event("draft-report", "report_question", manual=True),
        ],
    )

    result = promote_import_drafts(tmp_path, draft_path=draft_path)

    assert result.promoted == 2
    assert result.skipped_manual == 1
    events_path = tmp_path / "events" / "events.jsonl"
    rows = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
    assert [row["event_id"] for row in rows] == ["draft-green-diet", "draft-green-symptom"]
    assert all(row["import_status"] == "promoted" for row in rows)
    report = (tmp_path / "exports" / "draft_review_report.md").read_text(encoding="utf-8")
    assert "Promoted: 2" in report
    assert "Manual review required: 1" in report


def test_promote_import_drafts_does_not_duplicate_existing_events(tmp_path):
    initialize_data_dir(tmp_path)
    draft_path = write_drafts(tmp_path, [base_event("draft-green-diet", "diet_question")])
    promote_import_drafts(tmp_path, draft_path=draft_path)
    second = promote_import_drafts(tmp_path, draft_path=draft_path)

    rows = (tmp_path / "events" / "events.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(rows) == 1
    assert second.duplicates == 1


def test_generate_manual_review_queue_groups_without_full_private_text(tmp_path):
    initialize_data_dir(tmp_path)
    draft_path = write_drafts(
        tmp_path,
        [
            base_event("draft-report", "report_question", manual=True),
            base_event("draft-red", "symptom_qa", risk_level="red", manual=True),
            {
                **base_event("draft-med", "medication_question", manual=True),
                "user_message_summary": "A" * 260,
                "assistant_response_summary": "B" * 260,
            },
            base_event("draft-green-diet", "diet_question"),
        ],
    )

    queue_path = generate_manual_review_queue(tmp_path, draft_path=draft_path)
    content = queue_path.read_text(encoding="utf-8")

    assert queue_path == tmp_path / "exports" / "manual_review_queue.md"
    assert "Manual Review Queue" in content
    assert "draft-red" in content
    assert "draft-report" in content
    assert "draft-med" in content
    assert "draft-green-diet" not in content
    assert "AAAA" in content
    assert "A" * 220 not in content
    assert "- [ ] promote" in content
    assert "- [ ] skip" in content


def test_apply_manual_review_decisions_promotes_skips_and_creates_correction_drafts(tmp_path):
    initialize_data_dir(tmp_path)
    draft_path = write_drafts(
        tmp_path,
        [
            base_event("draft-promote", "report_question", manual=True),
            base_event("draft-skip", "symptom_qa", risk_level="red", manual=True),
            base_event("draft-correct", "medication_question", manual=True),
            base_event("draft-unchecked", "report_question", manual=True),
        ],
    )
    queue_path = tmp_path / "exports" / "manual_review_queue.md"
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    queue_path.write_text(
        """
# Manual Review Queue

### draft-promote
- decision:
  - [x] promote
  - [ ] skip
  - [ ] correction needed

### draft-skip
- decision:
  - [ ] promote
  - [x] skip
  - [ ] correction needed

### draft-correct
- decision:
  - [ ] promote
  - [ ] skip
  - [x] correction needed

### draft-unchecked
- decision:
  - [ ] promote
  - [ ] skip
  - [ ] correction needed
""",
        encoding="utf-8",
    )

    result = apply_manual_review_decisions(tmp_path, queue_path=queue_path, draft_path=draft_path)

    assert result.promoted == 1
    assert result.skipped == 1
    assert result.corrections_needed == 1
    assert result.unchecked == 1
    events = [json.loads(line) for line in (tmp_path / "events" / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [event["event_id"] for event in events] == ["draft-promote"]
    corrections = [
        json.loads(line)
        for line in (tmp_path / "events" / "correction_drafts.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert corrections[0]["event_type"] == "correction_draft"
    assert corrections[0]["target_event_id"] == "draft-correct"
    report = (tmp_path / "exports" / "manual_review_decisions_report.md").read_text(encoding="utf-8")
    assert "Promoted: 1" in report
    assert "Unchecked: 1" in report
