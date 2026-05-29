import json
import zipfile

from scripts.init_data_dir import initialize_data_dir
from pregnancy_copilot.importers.gemini_markdown import (
    extract_turns_from_markdown,
    import_gemini_zip_to_drafts,
)


SAMPLE_MARKDOWN = """---
sourceFile: "sample.md"
exportedBy: "Kortex"
---

# sample

--------------------------------------------------------------------------------

今天肚子有点紧，休息后好了，没有流血也没有流水

🤖 Assistant

这是绿色风险，可以先记录频率。

--------------------------------------------------------------------------------

这个 B 超数据是什么意思

🤖 Assistant

需要结合报告原文和医生结论解释。
"""


def test_extract_turns_from_kortex_markdown_blocks():
    turns = extract_turns_from_markdown(SAMPLE_MARKDOWN, source_name="sample.md")

    assert len(turns) == 2
    assert turns[0].user_text == "今天肚子有点紧，休息后好了，没有流血也没有流水"
    assert turns[0].assistant_text == "这是绿色风险，可以先记录频率。"
    assert turns[0].risk_level == "green"
    assert turns[1].event_type == "report_question"
    assert turns[1].requires_manual_review is True


def test_import_gemini_zip_writes_raw_files_draft_events_and_report(tmp_path):
    data_root = tmp_path / "pregnancy-data"
    initialize_data_dir(data_root)
    zip_path = tmp_path / "gemini.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("sample.md", SAMPLE_MARKDOWN)

    result = import_gemini_zip_to_drafts(zip_path, data_root)

    assert result.turn_count == 2
    assert result.raw_files_written == 1
    draft_path = data_root / "events" / "draft_import_events.jsonl"
    rows = [json.loads(line) for line in draft_path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 2
    assert rows[0]["source"] == "gemini_import"
    assert rows[0]["raw_source_path"].startswith("inbox/raw_gemini_exports/")
    assert rows[1]["requires_manual_review"] is True
    report = (data_root / "exports" / "gemini_import_report.md").read_text(encoding="utf-8")
    assert "Turns extracted: 2" in report
    assert "Manual review required: 1" in report
