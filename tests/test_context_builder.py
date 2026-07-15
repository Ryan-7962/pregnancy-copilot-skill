import json

from scripts.init_data_dir import initialize_data_dir
from pregnancy_copilot.context_builder import build_current_context, build_emotional_pattern, build_medical_timeline
from pregnancy_copilot.storage import PregnancyDataStore


def test_build_current_context_from_profile_and_events(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    store.append_event(
        {
            "schema_version": "0.1",
            "event_id": "event-001",
            "event_type": "symptom_qa",
            "timestamp": "2026-05-05T08:30:00+08:00",
            "gestational_age": "20w0d",
            "raw_source_path": "inbox/raw_feishu_messages/2026-05-05.md",
            "user_message_summary": "询问肚皮发紧是否正常",
            "assistant_response_summary": "休息后缓解，暂无红旗症状，建议记录频率。",
            "risk_level": "green",
            "doctor_question_candidates": ["肚皮发紧是否需要关注宫颈长度？"],
        }
    )
    store.append_event(
        {
            "schema_version": "0.1",
            "event_id": "event-002",
            "event_type": "symptom_qa",
            "timestamp": "2026-05-05T09:00:00+08:00",
            "gestational_age": "20w0d",
            "raw_source_path": "inbox/raw_feishu_messages/2026-05-05.md",
            "user_message_summary": "询问 B 超数据",
            "assistant_response_summary": "报告解释需要结合医生结论。",
            "risk_level": "yellow",
            "doctor_question_candidates": ["B 超异常描述是否需要复查？"],
        }
    )

    path = build_current_context(store)
    content = path.read_text(encoding="utf-8")

    assert path == tmp_path / "memory" / "current_context.md"
    assert "未设置" in content
    assert "W20+0" not in content
    assert "询问肚皮发紧是否正常" in content
    assert "yellow" in content
    assert "肚皮发紧是否需要关注宫颈长度？" in content
    assert "inbox/raw_feishu_messages/2026-05-05.md" in content


def test_read_events_skips_blank_lines(tmp_path):
    initialize_data_dir(tmp_path)
    events_path = tmp_path / "events" / "events.jsonl"
    events_path.write_text(
        "\n"
        + json.dumps({"schema_version": "0.1", "event_id": "event-001"}, ensure_ascii=False)
        + "\n\n",
        encoding="utf-8",
    )

    path = build_current_context(PregnancyDataStore(tmp_path))

    assert "event-001" in path.read_text(encoding="utf-8")


def test_current_context_separates_live_events_and_imported_low_risk_patterns(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    store.append_event(
        {
            "schema_version": "0.1",
            "event_id": "live-001",
            "event_type": "symptom_qa",
            "timestamp": "2026-05-05T08:30:00+08:00",
            "source": "feishu",
            "raw_source_path": "inbox/raw_feishu_messages/2026-05-05.md",
            "user_message_summary": "今天肚子有点紧",
            "assistant_response_summary": "绿色，记录频率。",
            "risk_level": "green",
        }
    )
    store.append_event(
        {
            "schema_version": "0.1",
            "event_id": "import-001",
            "event_type": "diet_question",
            "source": "gemini_import",
            "raw_source_path": "inbox/raw_gemini_exports/sample.md",
            "user_message_summary": "询问孕期饮食",
            "assistant_response_summary": "低风险饮食建议。",
            "risk_level": "green",
            "import_status": "promoted",
        }
    )
    draft_path = tmp_path / "events" / "draft_import_events.jsonl"
    draft_path.write_text(
        json.dumps(
            {
                "schema_version": "0.1",
                "event_id": "draft-report",
                "event_type": "report_question",
                "source": "gemini_import",
                "user_message_summary": "这个报告数值是什么意思",
                "risk_level": "yellow",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    path = build_current_context(store)
    content = path.read_text(encoding="utf-8")

    assert "## 最近实时事件" in content
    assert "今天肚子有点紧" in content
    assert "## 历史导入低风险模式" in content
    assert "diet_question: 1" in content
    assert "询问孕期饮食" in content
    assert "这个报告数值是什么意思" not in content


def test_current_context_summarizes_large_imports_without_expanding_all_history(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    for index in range(100):
        store.append_event(
            {
                "schema_version": "0.1",
                "event_id": f"import-{index:03d}",
                "event_type": "diet_question" if index % 2 == 0 else "symptom_qa",
                "source": "gemini_import",
                "raw_source_path": f"inbox/raw_gemini_exports/source-{index:03d}.md",
                "user_message_summary": f"历史导入低风险主题 {index:03d}",
                "assistant_response_summary": "低风险历史回复摘要。",
                "risk_level": "green",
                "import_status": "promoted",
            }
        )

    path = build_current_context(store)
    content = path.read_text(encoding="utf-8")

    assert "## 历史导入低风险模式" in content
    assert "diet_question: 50" in content
    assert "symptom_qa: 50" in content
    assert "历史导入低风险主题 099" in content
    assert "历史导入低风险主题 000" not in content
    assert len(content) < 12000


def test_build_medical_timeline_from_report_and_yellow_events(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    store.append_event(
        {
            "schema_version": "0.1",
            "event_id": "report-001",
            "event_type": "prenatal_report",
            "timestamp": "2026-05-05T10:00:00+08:00",
            "gestational_age": "8w2d",
            "raw_source_path": "reports/demo-ultrasound.md",
            "user_message_summary": "B 超报告提示需要复查",
            "risk_level": "yellow",
            "import_status": "promoted_manual",
        }
    )
    store.append_event(
        {
            "schema_version": "0.1",
            "event_id": "draft-report",
            "event_type": "prenatal_report",
            "timestamp": "2026-05-06T10:00:00+08:00",
            "gestational_age": "8w3d",
            "raw_source_path": "reports/draft.md",
            "user_message_summary": "未复核报告",
            "risk_level": "yellow",
            "import_status": "draft",
        }
    )

    path = build_medical_timeline(store)
    content = path.read_text(encoding="utf-8")

    assert path == tmp_path / "memory" / "medical_timeline.md"
    assert "B 超报告提示需要复查" in content
    assert "reports/demo-ultrasound.md" in content
    assert "未复核报告" not in content


def test_build_emotional_pattern_from_recent_emotion_events(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    store.append_event(
        {
            "schema_version": "0.1",
            "event_id": "emotion-001",
            "event_type": "symptom_qa",
            "timestamp": "2026-05-05T21:00:00+08:00",
            "gestational_age": "8w2d",
            "raw_source_path": "inbox/raw_feishu_messages/2026-05-05.md",
            "user_message_summary": "今天有点焦虑，担心报告结果",
            "assistant_response_summary": "先接住情绪，再整理问题问医生。",
            "risk_level": "green",
        }
    )

    path = build_emotional_pattern(store)
    content = path.read_text(encoding="utf-8")

    assert path == tmp_path / "memory" / "emotional_pattern.md"
    assert "焦虑" in content
    assert "担心报告结果" in content
    assert "先接住情绪" in content
