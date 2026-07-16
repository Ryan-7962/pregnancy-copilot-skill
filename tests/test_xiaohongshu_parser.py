from pathlib import Path

import pytest

from pregnancy_copilot.external_content.xiaohongshu import (
    canonicalize_xiaohongshu_url,
    extract_xiaohongshu_record,
    extract_xiaohongshu_urls,
    parse_initial_state,
)


FIXTURES = Path(__file__).parent / "fixtures" / "xiaohongshu"


def test_extract_urls_from_message_and_ignore_other_links():
    text = (
        "帮我看看 https://www.xiaohongshu.com/discovery/item/synthetic-post-001?xsec_token=secret "
        "以及短链 https://xhslink.com/aBc123 ，不要处理 https://example.com/article"
    )

    assert extract_xiaohongshu_urls(text) == [
        "https://www.xiaohongshu.com/discovery/item/synthetic-post-001?xsec_token=secret",
        "https://xhslink.com/aBc123",
    ]


def test_canonicalize_direct_url_removes_query_and_fragment():
    url = "https://www.xiaohongshu.com/explore/synthetic-post-001?xsec_token=secret#comments"

    assert canonicalize_xiaohongshu_url(url) == (
        "https://www.xiaohongshu.com/explore/synthetic-post-001"
    )


def test_canonicalize_short_link_validates_every_redirect():
    def valid_resolver(_url):
        return [
            "https://xhslink.com/aBc123",
            "https://www.xiaohongshu.com/discovery/item/synthetic-post-001?xsec_token=temporary",
        ]

    assert canonicalize_xiaohongshu_url("https://xhslink.com/aBc123", valid_resolver) == (
        "https://www.xiaohongshu.com/discovery/item/synthetic-post-001"
    )

    def invalid_resolver(_url):
        return ["https://xhslink.com/aBc123", "https://127.0.0.1/private"]

    with pytest.raises(ValueError, match="redirect|host"):
        canonicalize_xiaohongshu_url("https://xhslink.com/aBc123", invalid_resolver)


@pytest.mark.parametrize(
    "url",
    [
        "http://www.xiaohongshu.com/explore/id",
        "https://www.xiaohongshu.com.evil.test/explore/id",
        "https://user@www.xiaohongshu.com/explore/id",
        "https://localhost/explore/id",
        "https://[::1]/explore/id",
    ],
)
def test_canonicalize_rejects_unsafe_urls(url):
    with pytest.raises(ValueError):
        canonicalize_xiaohongshu_url(url)


def test_parse_initial_state_without_executing_javascript():
    html = (FIXTURES / "image_text_note.html").read_text(encoding="utf-8")

    state = parse_initial_state(html)

    note = state["note"]["noteDetailMap"]["synthetic-post-001"]["note"]
    assert note["video"] is None
    assert "undefined stays" in note["desc"]


def test_extract_image_text_record_keeps_media_urls_ephemeral():
    html = (FIXTURES / "image_text_note.html").read_text(encoding="utf-8")

    extraction = extract_xiaohongshu_record(
        html,
        canonical_url="https://www.xiaohongshu.com/discovery/item/synthetic-post-001",
        captured_at="2026-07-16T14:00:00+08:00",
        user_question="这条建议适合我吗？",
    )

    record = extraction.record
    assert record.source_id == "xhs-synthetic-post-001"
    assert record.content_type == "image_text"
    assert record.title == "Synthetic prenatal nutrition note"
    assert record.author_display_name == "Synthetic Author"
    assert record.tags == ["nutrition", "pregnancy"]
    assert record.extraction_methods == ["xiaohongshu_ssr"]
    assert len(record.media) == 2
    assert all(item.relative_path is None for item in record.media)
    assert extraction.image_urls == (
        "https://sns-img-qc.xhscdn.com/image-1.jpg?signature=temporary",
        "https://sns-img-qc.xhscdn.com/image-2.jpg?signature=temporary",
    )
    assert "signature=temporary" not in str(record.to_dict())


def test_extract_video_record_returns_stream_only_as_ephemeral_candidate():
    html = (FIXTURES / "video_note.html").read_text(encoding="utf-8")

    extraction = extract_xiaohongshu_record(
        html,
        canonical_url="https://www.xiaohongshu.com/explore/synthetic-video-001",
        captured_at="2026-07-16T14:05:00+08:00",
    )

    assert extraction.record.content_type == "video"
    assert extraction.record.author_display_name == "Synthetic Video Author"
    assert len(extraction.record.media) == 1
    assert extraction.record.media[0].kind == "video"
    assert extraction.video_urls == (
        "https://sns-video-hw.xhscdn.com/video.mp4?signature=temporary",
    )
    assert "signature=temporary" not in str(extraction.record.to_dict())


def test_parse_initial_state_rejects_missing_or_malformed_payload():
    with pytest.raises(ValueError, match="INITIAL_STATE"):
        parse_initial_state("<html><script>const x = {};</script></html>")

    with pytest.raises(ValueError, match="INITIAL_STATE"):
        parse_initial_state("<script>window.__INITIAL_STATE__={broken: true};</script>")
