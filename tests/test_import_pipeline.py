from __future__ import annotations

from zipfile import ZipFile

from pregnancy_copilot.importers.pipeline import run_gemini_import_pipeline
from pregnancy_copilot.storage import SCHEMA_VERSION


SAMPLE_MARKDOWN = """---
sourceFile: "sample.md"
exportedBy: "Kortex"
---

# sample

--------------------------------------------------------------------------------

今天可以吃苹果吗？

🤖 Assistant

可以作为普通饮食记录，但需要结合个人情况。

--------------------------------------------------------------------------------

B 超报告这个数值正常吗？

🤖 Assistant

报告问题需要医生确认。
"""


def test_run_gemini_import_pipeline_imports_promotes_queues_and_rebuilds_context(tmp_path):
    data_root = tmp_path / "pregnancy-data"
    (data_root / "memory").mkdir(parents=True)
    (data_root / "memory" / "profile.yaml").write_text(
        "\n".join(
            [
                f"schema_version: '{SCHEMA_VERSION}'",
                "current_gestational_age: 8w2d",
                "current_focus:",
                "  - 测试导入流水线",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    zip_path = tmp_path / "gemini.zip"
    with ZipFile(zip_path, "w") as archive:
        archive.writestr("sample.md", SAMPLE_MARKDOWN)

    result = run_gemini_import_pipeline(zip_path, data_root)

    assert result.import_result.turn_count == 2
    assert result.promotion_result.promoted == 1
    assert result.queue_path.exists()
    assert result.context_path.exists()
    assert result.pipeline_report_path.exists()

    events_text = (data_root / "events" / "events.jsonl").read_text(encoding="utf-8")
    assert "diet_question" in events_text
    assert "report_question" not in events_text

    context_text = result.context_path.read_text(encoding="utf-8")
    assert "历史导入低风险模式" in context_text
    assert "diet_question: 1" in context_text
    assert "report_question" not in context_text


def test_run_gemini_import_pipeline_initializes_new_data_root(tmp_path):
    data_root = tmp_path / "new-pregnancy-data"
    zip_path = tmp_path / "gemini.zip"
    with ZipFile(zip_path, "w") as archive:
        archive.writestr("sample.md", SAMPLE_MARKDOWN)

    result = run_gemini_import_pipeline(zip_path, data_root)

    assert result.import_result.turn_count == 2
    assert (data_root / "memory" / "profile.yaml").exists()
    assert result.context_path.exists()
