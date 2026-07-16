from pregnancy_copilot.context_package import build_host_context_package
from pregnancy_copilot.external_content.models import ExternalContentRecord
from pregnancy_copilot.external_content.storage import ExternalContentStore
from pregnancy_copilot.storage import PregnancyDataStore
from tests.helpers import make_profile_ready


def seed_source(tmp_path):
    ExternalContentStore(tmp_path).append_capture(
        ExternalContentRecord(
            source_id="xhs-synthetic-context-001",
            platform="xiaohongshu",
            canonical_url="https://www.xiaohongshu.com/explore/synthetic-context-001",
            captured_at="2026-07-16T17:00:00+08:00",
            content_type="text",
            title="Synthetic caffeine discussion",
            description="Long source body must never enter compact host context.",
            topic_tags=["咖啡因", "饮食"],
            extraction_status="complete",
        )
    )


def test_unrelated_question_does_not_load_external_content_index(tmp_path):
    make_profile_ready(tmp_path)
    seed_source(tmp_path)

    package = build_host_context_package(
        PregnancyDataStore(tmp_path),
        user_message="今天心情不错",
        intent="mood_support",
        channel="host_agent",
    )

    assert package["external_content_memory"] == []


def test_matching_topic_loads_only_compact_source_metadata(tmp_path):
    make_profile_ready(tmp_path)
    seed_source(tmp_path)

    package = build_host_context_package(
        PregnancyDataStore(tmp_path),
        user_message="之前那条咖啡因帖子结论是什么？",
        intent="external_content_audit",
        channel="host_agent",
    )

    assert package["external_content_memory"] == [
        {
            "source_id": "xhs-synthetic-context-001",
            "title": "Synthetic caffeine discussion",
            "captured_at": "2026-07-16T17:00:00+08:00",
            "topic_tags": ["咖啡因", "饮食"],
            "source_confidence": "social_media_unverified",
            "record_path": "external_sources/raw/20260716-xhs-synthetic-context-001.md",
        }
    ]
    assert "Long source body" not in str(package["external_content_memory"])
