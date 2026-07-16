import json
from pathlib import Path

from pregnancy_copilot.data_init import initialize_data_dir
from pregnancy_copilot.external_content.models import ExternalContentRecord, ExternalMediaItem
from pregnancy_copilot.external_content.storage import ExternalContentStore


def build_record(**overrides):
    values = {
        "source_id": "xhs-synthetic-post-001",
        "platform": "xiaohongshu",
        "canonical_url": "https://www.xiaohongshu.com/discovery/item/synthetic-post-001",
        "captured_at": "2026-07-16T10:00:00+08:00",
        "content_type": "image_text",
        "title": "Synthetic nutrition note",
        "description": "A synthetic post used only for tests.",
        "author_display_name": "Synthetic Author",
        "tags": ["nutrition"],
        "media": [ExternalMediaItem(kind="image", relative_path="external_sources/media/synthetic-post-001/P1.jpg")],
        "extraction_status": "complete",
        "extraction_methods": ["ssr_text"],
        "user_question": "Does this apply to me?",
        "topic_tags": ["diet"],
    }
    values.update(overrides)
    return ExternalContentRecord(**values)


def test_initialize_data_dir_creates_external_content_directories(tmp_path):
    initialize_data_dir(tmp_path)

    assert (tmp_path / "external_sources" / "raw").is_dir()
    assert (tmp_path / "external_sources" / "media").is_dir()


def test_record_defaults_to_unverified_and_rejects_signed_canonical_url():
    record = build_record()

    assert record.to_dict()["source_confidence"] == "social_media_unverified"
    assert record.to_dict()["author_identity_status"] == "unverified"

    try:
        build_record(canonical_url="https://www.xiaohongshu.com/discovery/item/id?xsec_token=secret")
    except ValueError as exc:
        assert "canonical_url" in str(exc)
    else:
        raise AssertionError("signed canonical URL must be rejected")


def test_append_capture_writes_markdown_jsonl_and_compact_index(tmp_path):
    initialize_data_dir(tmp_path)
    store = ExternalContentStore(tmp_path)

    result = store.append_capture(build_record())

    assert result.appended is True
    assert result.version == 1
    raw_path = tmp_path / result.raw_path
    assert raw_path.exists()
    raw_text = raw_path.read_text(encoding="utf-8")
    assert "social_media_unverified" in raw_text
    assert "Synthetic nutrition note" in raw_text
    events = [json.loads(line) for line in (tmp_path / "external_sources" / "index.jsonl").read_text().splitlines()]
    assert len(events) == 1
    assert events[0]["event_type"] == "capture"
    compact = (tmp_path / "memory" / "external_content_index.md").read_text(encoding="utf-8")
    assert "xhs-synthetic-post-001" in compact
    assert "A synthetic post used only for tests." not in compact


def test_identical_capture_is_idempotent_and_changed_content_appends_version(tmp_path):
    initialize_data_dir(tmp_path)
    store = ExternalContentStore(tmp_path)

    first = store.append_capture(build_record())
    duplicate = store.append_capture(build_record(captured_at="2026-07-16T11:00:00+08:00"))
    changed = store.append_capture(
        build_record(
            captured_at="2026-07-17T09:00:00+08:00",
            description="The synthetic post changed for a second captured version.",
        )
    )

    assert first.appended is True
    assert duplicate.appended is False
    assert duplicate.version == 1
    assert duplicate.raw_path == first.raw_path
    assert changed.appended is True
    assert changed.version == 2
    assert changed.raw_path != first.raw_path
    lines = (tmp_path / "external_sources" / "index.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    current = store.find_by_source_id("xhs-synthetic-post-001")
    assert current["version"] == 2
    assert current["record"]["description"].startswith("The synthetic post changed")


def test_compact_index_rebuild_is_byte_deterministic(tmp_path):
    initialize_data_dir(tmp_path)
    store = ExternalContentStore(tmp_path)
    store.append_capture(build_record())

    path = store.write_compact_index()
    before = path.read_bytes()
    store.write_compact_index()

    assert path.read_bytes() == before


def test_source_id_cannot_escape_data_root():
    try:
        build_record(source_id="../../outside")
    except ValueError as exc:
        assert "source_id" in str(exc)
    else:
        raise AssertionError("unsafe source ID must be rejected")
