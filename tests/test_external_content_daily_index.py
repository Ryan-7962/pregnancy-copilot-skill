import yaml

from pregnancy_copilot.daily_consolidation import consolidate_day
from pregnancy_copilot.external_content.models import ExternalContentRecord
from pregnancy_copilot.external_content.storage import ExternalContentStore
from pregnancy_copilot.storage import PregnancyDataStore
from tests.helpers import make_profile_ready


def test_daily_index_links_external_sources_without_copying_post_text(tmp_path):
    make_profile_ready(tmp_path)
    ExternalContentStore(tmp_path).append_capture(
        ExternalContentRecord(
            source_id="xhs-synthetic-daily-001",
            platform="xiaohongshu",
            canonical_url="https://www.xiaohongshu.com/explore/synthetic-daily-001",
            captured_at="2026-07-16T11:00:00+08:00",
            content_type="text",
            title="Synthetic daily source",
            description="This full synthetic source text must not be copied into the daily index.",
            extraction_status="complete",
        )
    )

    result = consolidate_day(PregnancyDataStore(tmp_path), "2026-07-16")
    day = yaml.safe_load(result.index_path.read_text(encoding="utf-8"))["days"]["2026-07-16"]

    assert day["external_source_count"] == 1
    assert day["external_sources"] == [
        {
            "source_id": "xhs-synthetic-daily-001",
            "record_path": "external_sources/raw/20260716-xhs-synthetic-daily-001.md",
        }
    ]
    assert "This full synthetic source text" not in result.index_path.read_text(encoding="utf-8")
