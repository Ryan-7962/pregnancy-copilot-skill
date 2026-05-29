from pregnancy_copilot.artifacts import (
    generate_baby_weekly_diary,
    generate_dad_diary,
    generate_daily_log,
    generate_husband_summary,
    generate_weekly_review,
    write_weekly_artifacts,
)
from pregnancy_copilot.storage import PregnancyDataStore, SCHEMA_VERSION
from scripts.init_data_dir import initialize_data_dir


def test_husband_summary_excludes_private_lines_and_keeps_actionable_support():
    daily_log = """
## 今日身体状态
- 腰酸，休息后缓解。
- [private] 她不想同步的一段敏感原文。

## 今日情绪
- 有些焦虑，希望被陪伴。
"""

    summary = generate_husband_summary(daily_log, privacy_level="summary")

    assert "她不想同步" not in summary
    assert "伴侣可以做的 3 件事" in summary
    assert "陪伴" in summary


def test_dad_diary_uses_title_format_and_non_medical_baby_status():
    diary = generate_dad_diary(
        raw_text="今天陪她去产检，她很紧张，我也认真记了医生说的话。",
        gestational_age="20w0d",
        mood="紧张转安心",
        baby_status="继续成长",
    )

    assert diary.startswith("# W20+0｜心情：紧张转安心｜宝宝状态：继续成长")
    assert "## 爸爸原文" in diary
    assert "## AI 整理版" in diary


def test_baby_weekly_diary_avoids_medical_promises():
    diary = generate_baby_weekly_diary(
        gestational_week="W20",
        weekly_review="妈妈这周有些焦虑，爸爸帮忙整理产检问题。",
        dad_diaries="爸爸说会认真陪伴。",
        prenatal_events="有一些报告问题准备问医生。",
        baby_nickname="小豆豆",
    )

    banned = ["我很健康", "一切正常", "妈妈不用担心"]
    assert "# W20 小豆豆周记" in diary
    assert "准备问医生" in diary
    assert all(phrase not in diary for phrase in banned)


def test_generate_daily_log_groups_same_day_events_and_hides_private_details(tmp_path):
    store = PregnancyDataStore(tmp_path)
    store.append_event(
        {
            "schema_version": SCHEMA_VERSION,
            "event_id": "evt-body",
            "event_type": "symptom_qa",
            "timestamp": "2026-05-05T08:30:00+08:00",
            "user_message_summary": "今天肚子有点紧，休息后好了",
            "assistant_response_summary": "未检测到明确红旗症状",
            "risk_level": "green",
            "action_items": ["记录频率"],
            "privacy_level": "summary",
        }
    )
    store.append_event(
        {
            "schema_version": SCHEMA_VERSION,
            "event_id": "evt-private",
            "event_type": "symptom_qa",
            "timestamp": "2026-05-05T11:00:00+08:00",
            "user_message_summary": "一段不想同步给伴侣的私密情绪",
            "risk_level": "yellow",
            "doctor_question_candidates": ["下次产检是否需要补充说明？"],
            "privacy_level": "private",
        }
    )
    store.append_event(
        {
            "schema_version": SCHEMA_VERSION,
            "event_id": "evt-other-day",
            "event_type": "symptom_qa",
            "timestamp": "2026-05-04T20:00:00+08:00",
            "user_message_summary": "昨天的内容",
            "risk_level": "green",
        }
    )

    path = generate_daily_log(store, "2026-05-05")
    text = path.read_text(encoding="utf-8")

    assert path == tmp_path / "daily_logs" / "2026-05-05.md"
    assert "# Daily Log 2026-05-05" in text
    assert "今天肚子有点紧" in text
    assert "一段不想同步" not in text
    assert "[private] evt-private" in text
    assert "下次产检是否需要补充说明？" in text
    assert "昨天的内容" not in text


def test_generate_weekly_review_aggregates_events_and_hides_private_details(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    store.append_event(
        {
            "schema_version": SCHEMA_VERSION,
            "event_id": "evt-week-body",
            "event_type": "symptom_qa",
            "timestamp": "2026-05-04T08:30:00+08:00",
            "user_message_summary": "肚子有点紧，休息后缓解",
            "assistant_response_summary": "绿色观察。",
            "risk_level": "green",
            "privacy_level": "summary",
        }
    )
    store.append_event(
        {
            "schema_version": SCHEMA_VERSION,
            "event_id": "evt-week-report",
            "event_type": "report_question",
            "timestamp": "2026-05-06T10:00:00+08:00",
            "user_message_summary": "B 超报告提示需要复查",
            "risk_level": "yellow",
            "doctor_question_candidates": ["这项报告是否需要提前复查？"],
            "privacy_level": "summary",
        }
    )
    store.append_event(
        {
            "schema_version": SCHEMA_VERSION,
            "event_id": "evt-week-private",
            "event_type": "symptom_qa",
            "timestamp": "2026-05-07T21:00:00+08:00",
            "user_message_summary": "一段私密情绪原文",
            "risk_level": "yellow",
            "privacy_level": "private",
        }
    )
    store.append_event(
        {
            "schema_version": SCHEMA_VERSION,
            "event_id": "evt-week-log",
            "event_type": "pregnancy_log",
            "timestamp": "2026-05-07T09:00:00+08:00",
            "user_message_summary": "今天体重 65kg，早餐吃了鸡蛋和牛奶",
            "risk_level": "not_applicable",
            "triage_required": False,
            "privacy_level": "summary",
        }
    )
    store.append_event(
        {
            "schema_version": SCHEMA_VERSION,
            "event_id": "evt-other-week",
            "event_type": "symptom_qa",
            "timestamp": "2026-05-12T09:00:00+08:00",
            "user_message_summary": "下周内容",
            "risk_level": "green",
            "privacy_level": "summary",
        }
    )

    review = generate_weekly_review(store, "2026-05-04", "2026-05-10")

    assert "# Weekly Review 2026-05-04 to 2026-05-10" in review
    assert "肚子有点紧" in review
    assert "B 超报告提示需要复查" in review
    assert "green: 1" in review
    assert "yellow: 2" in review
    assert "not_applicable" not in review
    assert "这项报告是否需要提前复查？" in review
    assert "今天体重 65kg" in review
    assert "一段私密情绪原文" not in review
    assert "[private] evt-week-private" in review
    assert "下周内容" not in review


def test_write_weekly_artifacts_creates_review_and_safe_baby_diary(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    profile = tmp_path / "memory" / "profile.yaml"
    profile.write_text(profile.read_text(encoding="utf-8").replace('baby_nickname: "宝宝"', 'baby_nickname: "小豆豆"'), encoding="utf-8")
    store.append_event(
        {
            "schema_version": SCHEMA_VERSION,
            "event_id": "evt-week-report",
            "event_type": "report_question",
            "timestamp": "2026-05-06T10:00:00+08:00",
            "gestational_age": "20w0d",
            "user_message_summary": "产检报告有问题准备问医生",
            "risk_level": "yellow",
            "privacy_level": "summary",
        }
    )
    store.append_event(
        {
            "schema_version": SCHEMA_VERSION,
            "event_id": "evt-dad",
            "event_type": "dad_diary",
            "timestamp": "2026-05-08T20:00:00+08:00",
            "user_message_summary": "爸爸说这周会认真陪伴",
            "risk_level": "green",
            "privacy_level": "summary",
        }
    )

    result = write_weekly_artifacts(store, "2026-05-04", "2026-05-10")
    review_text = result["weekly_review_path"].read_text(encoding="utf-8")
    diary_text = result["baby_diary_path"].read_text(encoding="utf-8")

    assert result["weekly_review_path"] == tmp_path / "weekly_reviews" / "2026-05-04_to_2026-05-10.md"
    assert result["baby_diary_path"] == tmp_path / "baby_diaries" / "week-2026-05-04_to_2026-05-10.md"
    assert "产检报告有问题准备问医生" in review_text
    assert "# W20 小豆豆周记" in diary_text
    assert "爸爸说这周会认真陪伴" in diary_text
    assert "准备问医生" in diary_text
    assert "一切正常" not in diary_text
