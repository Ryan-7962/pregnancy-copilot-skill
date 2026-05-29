import json

from pregnancy_copilot.importers.analysis import (
    analyze_import_drafts,
    analyze_review_lanes,
    write_import_category_report,
    write_review_lane_report,
    write_review_sample_report,
)


def test_analyze_import_drafts_counts_categories_without_raw_text(tmp_path):
    draft_path = tmp_path / "draft_import_events.jsonl"
    rows = [
        {
            "event_id": "diet-1",
            "event_type": "diet_question",
            "risk_level": "green",
            "requires_manual_review": False,
            "user_message_summary": "private diet text",
        },
        {
            "event_id": "report-1",
            "event_type": "report_question",
            "risk_level": "yellow",
            "requires_manual_review": True,
            "user_message_summary": "private report text",
        },
        {
            "event_id": "symptom-1",
            "event_type": "symptom_qa",
            "risk_level": "red",
            "requires_manual_review": True,
            "assistant_response_summary": "private response text",
        },
    ]
    draft_path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")

    analysis = analyze_import_drafts(draft_path)

    assert analysis.total == 3
    assert analysis.auto_promotable == 1
    assert analysis.manual_required == 2
    assert analysis.by_event_type["diet_question"] == 1
    assert analysis.by_risk_level["red"] == 1
    assert analysis.manual_by_event_type["report_question"] == 1

    report_path = write_import_category_report(draft_path, tmp_path / "report.md")
    report = report_path.read_text(encoding="utf-8")
    assert "diet_question: 1" in report
    assert "yellow: 1" in report
    assert "private diet text" not in report
    assert "private report text" not in report
    assert "private response text" not in report


def test_write_review_sample_report_groups_manual_items_without_private_summaries(tmp_path):
    draft_path = tmp_path / "draft_import_events.jsonl"
    rows = [
        {
            "event_id": "manual-report-red",
            "event_type": "report_question",
            "risk_level": "red",
            "requires_manual_review": True,
            "raw_source_path": "inbox/raw_gemini_exports/source-a.md",
            "turn_index": 10,
            "user_message_summary": "private report summary",
            "assistant_response_summary": "private report answer",
        },
        {
            "event_id": "manual-med-yellow",
            "event_type": "medication_question",
            "risk_level": "yellow",
            "requires_manual_review": True,
            "raw_source_path": "inbox/raw_gemini_exports/source-b.md",
            "turn_index": 11,
            "user_message_summary": "private medication summary",
        },
        {
            "event_id": "auto-diet-green",
            "event_type": "diet_question",
            "risk_level": "green",
            "requires_manual_review": False,
            "raw_source_path": "inbox/raw_gemini_exports/source-c.md",
            "turn_index": 12,
            "user_message_summary": "private auto summary",
        },
    ]
    draft_path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")

    report_path = write_review_sample_report(draft_path, tmp_path / "sample.md", per_bucket=2)
    report = report_path.read_text(encoding="utf-8")

    assert "report_question / red" in report
    assert "medication_question / yellow" in report
    assert "manual-report-red" in report
    assert "manual-med-yellow" in report
    assert "auto-diet-green" not in report
    assert "private report summary" not in report
    assert "private report answer" not in report
    assert "private medication summary" not in report
    assert "private auto summary" not in report


def test_review_lane_report_routes_manual_items_without_private_summaries(tmp_path):
    draft_path = tmp_path / "draft_import_events.jsonl"
    rows = [
        {
            "event_id": "report-cervix",
            "event_type": "report_question",
            "risk_level": "green",
            "requires_manual_review": True,
            "user_message_summary": "private 宫颈管长度 summary",
            "assistant_response_summary": "private report answer",
        },
        {
            "event_id": "medication-dose",
            "event_type": "medication_question",
            "risk_level": "green",
            "requires_manual_review": True,
            "user_message_summary": "private 钙片 summary",
        },
        {
            "event_id": "red-symptom",
            "event_type": "symptom_qa",
            "risk_level": "red",
            "requires_manual_review": True,
            "user_message_summary": "private symptom summary",
        },
    ]
    draft_path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")

    analysis = analyze_review_lanes(draft_path)

    assert analysis.by_lane["structured_medical_candidate"] == 1
    assert analysis.by_lane["medication_review_candidate"] == 1
    assert analysis.by_lane["urgent_or_yellow_risk_review"] == 1
    assert analysis.by_medical_signal["cervical_length"] == 1
    assert analysis.by_medical_signal["medication_or_supplement"] == 1

    report_path = write_review_lane_report(draft_path, tmp_path / "lanes.md")
    report = report_path.read_text(encoding="utf-8")
    assert "structured_medical_candidate: 1" in report
    assert "cervical_length: 1" in report
    assert "report-cervix" in report
    assert "private 宫颈管长度 summary" not in report
    assert "private report answer" not in report
    assert "private symptom summary" not in report
