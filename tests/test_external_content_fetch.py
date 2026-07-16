from dataclasses import dataclass

import pytest

from pregnancy_copilot.external_content.fetch import (
    CredentialsRequiredError,
    FetchLimitError,
    FetchLimits,
    SafeHttpTransport,
    download_xiaohongshu_media,
    fetch_xiaohongshu_post,
)


HTML = """<script>window.__INITIAL_STATE__={"note":{"noteDetailMap":{"synthetic-post-001":{"note":{"noteId":"synthetic-post-001","title":"Synthetic","desc":"Fixture only","tagList":[],"user":{},"imageList":[]}}}}};</script>"""
COOKIE = "a1=fixture-a1-secret; web_session=fixture-session-secret"


@dataclass
class FakeResponse:
    status: int
    headers: dict[str, str]
    body: bytes


class FakeSender:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def __call__(self, request, timeout):
        self.requests.append((request, timeout))
        if not self.responses:
            raise AssertionError("unexpected request")
        return self.responses.pop(0)


def test_fetch_short_link_uses_mobile_ua_cookie_and_validates_redirect():
    sender = FakeSender(
        [
            FakeResponse(
                302,
                {
                    "Location": "https://www.xiaohongshu.com/discovery/item/synthetic-post-001?xsec_token=temp"
                },
                b"",
            ),
            FakeResponse(200, {"Content-Type": "text/html"}, HTML.encode()),
        ]
    )
    transport = SafeHttpTransport(sender=sender)

    fetched = fetch_xiaohongshu_post(
        "https://xhslink.com/fixture",
        captured_at="2026-07-16T15:00:00+08:00",
        cookie_header=COOKIE,
        transport=transport,
    )

    assert fetched.extraction.record.canonical_url == (
        "https://www.xiaohongshu.com/discovery/item/synthetic-post-001"
    )
    assert len(sender.requests) == 2
    first_request = sender.requests[0][0]
    assert "Mobile" in first_request.headers["User-Agent"]
    assert first_request.headers["Cookie"] == COOKIE


def test_direct_shared_url_keeps_xsec_token_for_request_but_not_record():
    sender = FakeSender([FakeResponse(200, {"Content-Type": "text/html"}, HTML.encode())])
    transport = SafeHttpTransport(sender=sender)
    shared_url = (
        "https://www.xiaohongshu.com/discovery/item/synthetic-post-001"
        "?xsec_token=temporary-request-only&xsec_source=pc_feed"
    )

    fetched = fetch_xiaohongshu_post(
        shared_url,
        captured_at="2026-07-16T15:00:00+08:00",
        cookie_header=COOKIE,
        transport=transport,
    )

    assert sender.requests[0][0].url == shared_url
    assert "xsec_token" not in fetched.extraction.record.canonical_url


def test_transport_rejects_redirect_before_contacting_untrusted_host():
    sender = FakeSender(
        [FakeResponse(302, {"Location": "https://evil.test/private"}, b"")]
    )
    transport = SafeHttpTransport(sender=sender)

    with pytest.raises(ValueError, match="redirect|host"):
        fetch_xiaohongshu_post(
            "https://xhslink.com/fixture",
            captured_at="2026-07-16T15:00:00+08:00",
            cookie_header=COOKIE,
            transport=transport,
        )

    assert len(sender.requests) == 1


def test_transport_enforces_body_limit_without_leaking_cookie():
    sender = FakeSender([FakeResponse(200, {}, b"x" * 11)])
    transport = SafeHttpTransport(sender=sender, limits=FetchLimits(max_html_bytes=10))

    with pytest.raises(FetchLimitError) as exc_info:
        fetch_xiaohongshu_post(
            "https://www.xiaohongshu.com/explore/synthetic-post-001",
            captured_at="2026-07-16T15:00:00+08:00",
            cookie_header=COOKIE,
            transport=transport,
        )

    assert "fixture-a1-secret" not in str(exc_info.value)


@pytest.mark.parametrize("status", [401, 403])
def test_auth_response_returns_credential_guidance_without_secret(status):
    sender = FakeSender([FakeResponse(status, {}, b"denied")])
    transport = SafeHttpTransport(sender=sender)

    with pytest.raises(CredentialsRequiredError) as exc_info:
        fetch_xiaohongshu_post(
            "https://www.xiaohongshu.com/explore/synthetic-post-001",
            captured_at="2026-07-16T15:00:00+08:00",
            cookie_header=COOKIE,
            transport=transport,
        )

    message = str(exc_info.value)
    assert "PREGNANCY_COPILOT_XHS_COOKIE_FILE" in message
    assert "fixture-session-secret" not in message


def test_transport_enforces_redirect_limit():
    sender = FakeSender(
        [
            FakeResponse(302, {"Location": "https://xhslink.com/two"}, b""),
            FakeResponse(302, {"Location": "https://xhslink.com/three"}, b""),
        ]
    )
    transport = SafeHttpTransport(sender=sender, limits=FetchLimits(max_redirects=1))

    with pytest.raises(FetchLimitError, match="redirect"):
        fetch_xiaohongshu_post(
            "https://xhslink.com/one",
            captured_at="2026-07-16T15:00:00+08:00",
            cookie_header=COOKIE,
            transport=transport,
        )


def test_media_download_allows_xhs_cdn_and_never_persists_signed_url(tmp_path):
    sender = FakeSender([FakeResponse(200, {"Content-Type": "image/jpeg"}, b"synthetic-image")])
    destination = tmp_path / "P1.jpg"

    result = download_xiaohongshu_media(
        "https://sns-img-qc.xhscdn.com/image.jpg?signature=temporary",
        destination,
        cookie_header=COOKIE,
        referer="https://www.xiaohongshu.com/explore/synthetic-post-001",
        sender=sender,
        resolver=lambda _host, _port: [(None, None, None, None, ("8.8.8.8", 443))],
    )

    assert result == destination
    assert destination.read_bytes() == b"synthetic-image"
    request = sender.requests[0][0]
    assert request.headers["Cookie"] == COOKIE
    assert request.headers["Referer"].startswith("https://www.xiaohongshu.com/")
    assert "signature=temporary" not in destination.read_text(encoding="latin-1")


def test_media_download_rejects_non_xhs_cdn_and_private_resolution(tmp_path):
    sender = FakeSender([FakeResponse(200, {}, b"data")])
    with pytest.raises(ValueError, match="media host"):
        download_xiaohongshu_media(
            "https://evil.test/image.jpg",
            tmp_path / "P1.jpg",
            sender=sender,
            resolver=lambda _host, _port: [(None, None, None, None, ("8.8.8.8", 443))],
        )
    with pytest.raises(ValueError, match="public"):
        download_xiaohongshu_media(
            "https://sns-img-qc.xhscdn.com/image.jpg",
            tmp_path / "P1.jpg",
            sender=sender,
            resolver=lambda _host, _port: [(None, None, None, None, ("127.0.0.1", 443))],
        )
