from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import os
from pathlib import Path
import socket
import tempfile
from typing import Callable, Mapping
from urllib.error import HTTPError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from pregnancy_copilot.external_content.xiaohongshu import (
    ALLOWED_HOSTS,
    SHORT_LINK_HOSTS,
    XiaohongshuExtraction,
    canonicalize_xiaohongshu_url,
    extract_xiaohongshu_record,
)


MOBILE_USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 Mobile/15E148"
)


class FetchError(RuntimeError):
    pass


class FetchLimitError(FetchError):
    pass


class CredentialsRequiredError(FetchError):
    pass


@dataclass(frozen=True)
class FetchLimits:
    max_redirects: int = 5
    max_html_bytes: int = 2 * 1024 * 1024
    timeout_seconds: float = 15.0


@dataclass(frozen=True)
class HttpRequest:
    url: str
    headers: dict[str, str]


@dataclass(frozen=True)
class HttpResponse:
    status: int
    headers: Mapping[str, str]
    body: bytes


@dataclass(frozen=True)
class TransportResult:
    final_url: str
    redirect_chain: tuple[str, ...]
    status: int
    headers: Mapping[str, str]
    body: bytes


@dataclass(frozen=True)
class FetchedXiaohongshuPost:
    extraction: XiaohongshuExtraction
    redirect_count: int


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class SafeHttpTransport:
    def __init__(
        self,
        *,
        sender: Callable[[HttpRequest, float], HttpResponse] | None = None,
        limits: FetchLimits | None = None,
    ) -> None:
        self.limits = limits or FetchLimits()
        self.sender = sender or self._default_sender

    def fetch_xiaohongshu_html(self, url: str, headers: dict[str, str]) -> TransportResult:
        current = url
        chain = [url]
        redirects = 0
        while True:
            _validate_xhs_request_url(current)
            response = self.sender(HttpRequest(url=current, headers=dict(headers)), self.limits.timeout_seconds)
            if response.status in {301, 302, 303, 307, 308}:
                if redirects >= self.limits.max_redirects:
                    raise FetchLimitError("Xiaohongshu redirect limit exceeded")
                location = _header(response.headers, "Location")
                if not location:
                    raise FetchError("Xiaohongshu redirect did not include a target")
                target = urljoin(current, location)
                try:
                    _validate_xhs_request_url(target)
                except ValueError as exc:
                    raise ValueError("Unsafe Xiaohongshu redirect host") from exc
                redirects += 1
                chain.append(target)
                current = target
                continue
            if len(response.body) > self.limits.max_html_bytes:
                raise FetchLimitError("Xiaohongshu HTML response exceeded the configured byte limit")
            return TransportResult(
                final_url=current,
                redirect_chain=tuple(chain),
                status=response.status,
                headers=response.headers,
                body=response.body,
            )

    def _default_sender(self, request: HttpRequest, timeout: float) -> HttpResponse:
        opener = build_opener(_NoRedirect())
        native_request = Request(request.url, headers=request.headers, method="GET")
        try:
            response = opener.open(native_request, timeout=timeout)
        except HTTPError as exc:
            response = exc
        with response:
            body = response.read(self.limits.max_html_bytes + 1)
            return HttpResponse(
                status=int(response.status),
                headers=dict(response.headers.items()),
                body=body,
            )


def fetch_xiaohongshu_post(
    url: str,
    *,
    captured_at: str,
    cookie_header: str | None,
    transport: SafeHttpTransport | None = None,
    user_question: str | None = None,
) -> FetchedXiaohongshuPost:
    client = transport or SafeHttpTransport()
    headers = {
        "User-Agent": MOBILE_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.5",
    }
    if cookie_header:
        headers["Cookie"] = cookie_header
    result = client.fetch_xiaohongshu_html(url, headers)
    if result.status in {401, 403}:
        raise CredentialsRequiredError(
            "Xiaohongshu access requires a current local Cookie; configure "
            "PREGNANCY_COPILOT_XHS_COOKIE_FILE in the Agent environment"
        )
    if result.status < 200 or result.status >= 300:
        raise FetchError(f"Xiaohongshu returned HTTP status {result.status}")

    if urlsplit(url).hostname in SHORT_LINK_HOSTS:
        canonical = canonicalize_xiaohongshu_url(url, lambda _url: result.redirect_chain)
    else:
        canonical = canonicalize_xiaohongshu_url(result.final_url)
    try:
        html = result.body.decode("utf-8")
        extraction = extract_xiaohongshu_record(
            html,
            canonical_url=canonical,
            captured_at=captured_at,
            user_question=user_question,
        )
    except (UnicodeDecodeError, ValueError) as exc:
        if not cookie_header:
            raise CredentialsRequiredError(
                "Xiaohongshu page could not be extracted; configure "
                "PREGNANCY_COPILOT_XHS_COOKIE_FILE in the Agent environment"
            ) from exc
        raise FetchError("Xiaohongshu page did not contain an extractable post payload") from exc
    return FetchedXiaohongshuPost(extraction=extraction, redirect_count=len(result.redirect_chain) - 1)


def download_xiaohongshu_media(
    url: str,
    destination: str | Path,
    *,
    cookie_header: str | None = None,
    referer: str | None = None,
    sender: Callable[[HttpRequest, float], HttpResponse] | None = None,
    resolver: Callable = socket.getaddrinfo,
    timeout_seconds: float = 20.0,
    max_bytes: int = 20 * 1024 * 1024,
    max_redirects: int = 3,
) -> Path:
    current = url
    headers = {"User-Agent": MOBILE_USER_AGENT, "Accept": "image/*,video/*;q=0.9,*/*;q=0.1"}
    if cookie_header:
        headers["Cookie"] = cookie_header
    if referer:
        headers["Referer"] = referer
    send = sender or (lambda request, timeout: _default_media_sender(request, timeout, max_bytes))
    redirects = 0
    while True:
        _validate_media_url(current, resolver)
        response = send(HttpRequest(url=current, headers=dict(headers)), timeout_seconds)
        if response.status in {301, 302, 303, 307, 308}:
            if redirects >= max_redirects:
                raise FetchLimitError("Xiaohongshu media redirect limit exceeded")
            location = _header(response.headers, "Location")
            if not location:
                raise FetchError("Xiaohongshu media redirect has no target")
            current = urljoin(current, location)
            redirects += 1
            continue
        if response.status < 200 or response.status >= 300:
            raise FetchError(f"Xiaohongshu media returned HTTP status {response.status}")
        if len(response.body) > max_bytes:
            raise FetchLimitError("Xiaohongshu media exceeded the configured byte limit")
        break

    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(response.body)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return path


def _validate_xhs_request_url(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Only credential-free HTTPS Xiaohongshu URLs are allowed")
    host = parsed.hostname.rstrip(".").lower()
    if host not in ALLOWED_HOSTS:
        raise ValueError("URL host is not an allowed Xiaohongshu host")


def _validate_media_url(url: str, resolver: Callable) -> None:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Only credential-free HTTPS media URLs are allowed")
    host = parsed.hostname.rstrip(".").lower()
    allowed = host == "xhscdn.com" or host.endswith(".xhscdn.com") or host == "xiaohongshu.com" or host.endswith(
        ".xiaohongshu.com"
    )
    if not allowed:
        raise ValueError("Xiaohongshu media host is not allowlisted")
    try:
        addresses = resolver(host, 443)
    except OSError as exc:
        raise FetchError("Xiaohongshu media host could not be resolved") from exc
    if not addresses:
        raise FetchError("Xiaohongshu media host could not be resolved")
    for address_info in addresses:
        address = str(address_info[4][0]).split("%", 1)[0]
        parsed_address = ipaddress.ip_address(address)
        if (
            parsed_address.is_private
            or parsed_address.is_loopback
            or parsed_address.is_link_local
            or parsed_address.is_reserved
            or parsed_address.is_unspecified
        ):
            raise ValueError("Xiaohongshu media must resolve only to public addresses")


def _default_media_sender(request: HttpRequest, timeout: float, max_bytes: int) -> HttpResponse:
    opener = build_opener(_NoRedirect())
    native_request = Request(request.url, headers=request.headers, method="GET")
    try:
        response = opener.open(native_request, timeout=timeout)
    except HTTPError as exc:
        response = exc
    with response:
        return HttpResponse(
            status=int(response.status),
            headers=dict(response.headers.items()),
            body=response.read(max_bytes + 1),
        )


def _header(headers: Mapping[str, str], name: str) -> str | None:
    lowered = name.lower()
    for key, value in headers.items():
        if key.lower() == lowered:
            return value
    return None
