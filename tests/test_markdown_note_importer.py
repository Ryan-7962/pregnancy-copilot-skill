import json

from pregnancy_copilot.importers.markdown_notes import import_markdown_notes_to_drafts


def test_import_notebooklm_markdown_notes_to_manual_review_drafts(tmp_path):
    source_dir = tmp_path / "notebooklm"
    source_dir.mkdir()
    (source_dir / "summary.md").write_text("这是 NotebookLM 汇总，提到饮食和一次检查。", encoding="utf-8")

    result = import_markdown_notes_to_drafts(
        source_dir=source_dir,
        data_root=tmp_path / "pregnancy-data",
        source="notebooklm_import",
        raw_subdir="raw_notebooklm_exports",
        default_event_type="imported_note",
    )

    rows = [
        json.loads(line)
        for line in result.draft_events_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert result.source_count == 1
    assert rows[0]["source"] == "notebooklm_import"
    assert rows[0]["event_type"] == "imported_note"
    assert rows[0]["requires_manual_review"] is True
    assert rows[0]["raw_source_path"].startswith("inbox/raw_notebooklm_exports/")


def test_import_obsidian_report_notes_to_reports_and_manual_review_drafts(tmp_path):
    source_dir = tmp_path / "obsidian"
    source_dir.mkdir()
    (source_dir / "2026-05-05-ultrasound.md").write_text("B 超报告：示例内容。医生建议复查。", encoding="utf-8")

    result = import_markdown_notes_to_drafts(
        source_dir=source_dir,
        data_root=tmp_path / "pregnancy-data",
        source="obsidian_import",
        raw_subdir="raw_obsidian_notes",
        default_event_type="prenatal_report",
        copy_to_reports=True,
    )

    rows = [
        json.loads(line)
        for line in result.draft_events_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert result.source_count == 1
    assert rows[0]["event_type"] == "prenatal_report"
    assert rows[0]["risk_level"] == "yellow"
    assert rows[0]["requires_manual_review"] is True
    assert (tmp_path / "pregnancy-data" / "reports" / "001-2026-05-05-ultrasound.md").exists()
