import yaml

from pregnancy_copilot.source_confidence import import_obsidian_gemini_state
from pregnancy_copilot.storage import PregnancyDataStore
from scripts.init_data_dir import initialize_data_dir


def test_import_obsidian_gemini_state_reads_only_refined_state_layer(tmp_path):
    source = tmp_path / "Gemini"
    source.mkdir()
    (source / "raw-chat.md").write_text("raw private text should not be copied", encoding="utf-8")
    refined = source / "状态提炼"
    refined.mkdir()
    (refined / "用户状态卡-2026-05-24.md").write_text(
        "\n".join(
            [
                "# 状态卡",
                "## 报告支持的事实",
                "| 主题 | 当前记录 | 可信度 | 来源 |",
                "|---|---|---|---|",
                "| 宫颈长径 | 29 mm，需随访 | report_verified | [[报告A]] |",
                "## 对话提炼",
                "| 主题 | 线索 | 可信度 | 来源 |",
                "|---|---|---|---|",
                "| 情绪模式 | 对风险边界敏感 | gemini_inferred | [[对话A]] |",
            ]
        ),
        encoding="utf-8",
    )
    (refined / "Gemini待核对清单-2026-05-24.md").write_text(
        "\n".join(
            [
                "# 待核对",
                "## 高优先级",
                "| 项目 | 当前线索 | 为什么要核对 | 来源 |",
                "|---|---|---|---|",
                "| OGTT 糖耐 | 已到时间窗 | 需要实际报告 | [[对话B]] |",
                "## 中优先级",
                "| 项目 | 当前线索 | 处理建议 | 来源 |",
                "|---|---|---|---|",
                "| 运动权限 | 是否解禁未知 | 下次问医生 | [[对话C]] |",
            ]
        ),
        encoding="utf-8",
    )
    initialize_data_dir(tmp_path / "data")
    store = PregnancyDataStore(tmp_path / "data")

    result = import_obsidian_gemini_state(source, store)

    assert result["source_files_read"] == 2
    assert result["raw_files_read"] == 0
    assert result["current_context"].endswith("memory/current_context.md")
    assert (store.root / "memory" / "current_context.md").exists()
    confidence = yaml.safe_load((store.root / "memory" / "source_confidence.yaml").read_text(encoding="utf-8"))
    assert confidence["summary"]["report_verified"] == 1
    assert confidence["summary"]["gemini_inferred"] == 1
    assert confidence["entries"][0]["topic"] == "宫颈长径"
    assert "raw private text" not in (store.root / "memory" / "source_confidence.yaml").read_text(encoding="utf-8")
    review = yaml.safe_load((store.root / "memory" / "open_review_items.yaml").read_text(encoding="utf-8"))
    assert review["summary"]["high"] == 1
    assert review["summary"]["medium"] == 1
    assert review["items"][0]["item"] == "OGTT 糖耐"
    context = (store.root / "memory" / "gemini_state_summary.md").read_text(encoding="utf-8")
    assert "只读取状态提炼层" in context


def test_current_context_includes_confidence_and_review_memory(tmp_path):
    source = tmp_path / "Gemini"
    refined = source / "状态提炼"
    refined.mkdir(parents=True)
    (refined / "用户状态卡-2026-05-24.md").write_text(
        "\n".join(
            [
                "| 主题 | 当前记录 | 可信度 | 来源 |",
                "|---|---|---|---|",
                "| 甲功 | TSH 旧值需复查 | report_verified | [[报告]] |",
            ]
        ),
        encoding="utf-8",
    )
    (refined / "Gemini待核对清单-2026-05-24.md").write_text(
        "\n".join(
            [
                "## 高优先级",
                "| 项目 | 当前线索 | 为什么要核对 | 来源 |",
                "|---|---|---|---|",
                "| 甲功复查 | 旧报告超过 3 个月 | 需要新报告 | [[状态卡]] |",
            ]
        ),
        encoding="utf-8",
    )
    initialize_data_dir(tmp_path / "data")
    store = PregnancyDataStore(tmp_path / "data")

    import_obsidian_gemini_state(source, store)
    from pregnancy_copilot.context_builder import build_current_context

    text = build_current_context(store).read_text(encoding="utf-8")

    assert "来源可信度摘要" in text
    assert "report_verified: 1" in text
    assert "待核对事项" in text
    assert "甲功复查" in text
    assert "Gemini 历史只能作为线索" in text


def test_import_obsidian_gemini_state_initializes_empty_data_root(tmp_path):
    source = tmp_path / "Gemini"
    refined = source / "状态提炼"
    refined.mkdir(parents=True)
    (refined / "用户状态卡-2026-05-24.md").write_text(
        "\n".join(
            [
                "| 主题 | 当前记录 | 可信度 | 来源 |",
                "|---|---|---|---|",
                "| 体重 | 50kg | user_reported | [[状态]] |",
            ]
        ),
        encoding="utf-8",
    )

    store = PregnancyDataStore(tmp_path / "empty-data")
    result = import_obsidian_gemini_state(source, store)

    assert result["current_context"].endswith("memory/current_context.md")
    assert (store.root / "memory" / "profile.yaml").exists()
    assert (store.root / "memory" / "current_context.md").exists()
