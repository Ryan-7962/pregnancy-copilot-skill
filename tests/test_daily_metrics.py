import yaml

from pregnancy_copilot.daily_metrics import build_daily_metrics_index, extract_weight_kg
from pregnancy_copilot.storage import PregnancyDataStore, SCHEMA_VERSION
from scripts.init_data_dir import initialize_data_dir


def test_extract_weight_kg_supports_common_chinese_formats():
    assert extract_weight_kg("今天体重 65kg，早餐吃了鸡蛋") == 65
    assert extract_weight_kg("晨起体重：50.85 kg") == 50.85
    assert extract_weight_kg("今天心情不错") is None


def test_build_daily_metrics_index_tracks_weight_trend_and_daily_logs(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    store.append_event(
        {
            "schema_version": SCHEMA_VERSION,
            "event_id": "evt-weight-old",
            "event_type": "pregnancy_log",
            "timestamp": "2026-05-06T08:00:00+08:00",
            "user_message_summary": "晨起体重 50.6kg，早餐吃了鸡蛋牛奶",
            "risk_level": "not_applicable",
            "triage_required": False,
            "privacy_level": "summary",
        }
    )
    store.append_event(
        {
            "schema_version": SCHEMA_VERSION,
            "event_id": "evt-mood",
            "event_type": "mood_support",
            "timestamp": "2026-05-07T21:00:00+08:00",
            "user_message_summary": "今天有点焦虑，晚上担心睡不好",
            "risk_level": "not_applicable",
            "triage_required": False,
            "privacy_level": "summary",
        }
    )
    store.append_event(
        {
            "schema_version": SCHEMA_VERSION,
            "event_id": "evt-weight-new",
            "event_type": "pregnancy_log",
            "timestamp": "2026-05-08T08:00:00+08:00",
            "user_message_summary": "今天体重 50.85kg，晚饭后散步 20 分钟，睡眠 7 小时",
            "risk_level": "not_applicable",
            "triage_required": False,
            "privacy_level": "summary",
        }
    )
    store.append_event(
        {
            "schema_version": SCHEMA_VERSION,
            "event_id": "evt-private",
            "event_type": "pregnancy_log",
            "timestamp": "2026-05-08T22:00:00+08:00",
            "user_message_summary": "一段 private 体重 99kg",
            "risk_level": "not_applicable",
            "triage_required": False,
            "privacy_level": "private",
        }
    )

    result = build_daily_metrics_index(store)

    assert result["days"]["2026-05-06"]["weight"]["value"] == 50.6
    assert result["days"]["2026-05-08"]["weight"]["value"] == 50.85
    assert result["weight_trend"]["latest"]["value"] == 50.85
    assert result["weight_trend"]["previous"]["value"] == 50.6
    assert result["weight_trend"]["delta_kg"] == 0.25
    assert result["days"]["2026-05-07"]["mood_entries"][0]["summary"] == "今天有点焦虑，晚上担心睡不好"
    assert result["days"]["2026-05-08"]["activity_entries"][0]["event_id"] == "evt-weight-new"
    assert "evt-private" not in yaml.safe_dump(result, allow_unicode=True)

    saved = yaml.safe_load((tmp_path / "memory" / "daily_metrics.yaml").read_text(encoding="utf-8"))
    assert saved["weight_trend"]["latest"]["source_event_id"] == "evt-weight-new"
    markdown = (tmp_path / "memory" / "daily_metrics.md").read_text(encoding="utf-8")
    assert "## 体重趋势" in markdown
    assert "50.85kg" in markdown
    assert "今天有点焦虑" in markdown
    assert "evt-private" not in markdown
    assert "99kg" not in markdown
