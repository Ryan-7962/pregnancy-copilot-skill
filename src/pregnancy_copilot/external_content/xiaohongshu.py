from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
import ipaddress
import json
import re
from typing import Any, Callable, Sequence
from urllib.parse import urlsplit, urlunsplit

from pregnancy_copilot.external_content.models import ExternalContentRecord, ExternalMediaItem
from pregnancy_copilot.storage import safe_path_component


ALLOWED_HOSTS = {
    "www.xiaohongshu.com",
    "xiaohongshu.com",
    "xhslink.com",
    "www.xhslink.com",
}
SHORT_LINK_HOSTS = {"xhslink.com", "www.xhslink.com"}
URL_PATTERN = re.compile(r"https://[^\s<>\]\[\)（），,。！]+", re.IGNORECASE)


@dataclass(frozen=True)
class XiaohongshuExtraction:
    record: ExternalContentRecord
    image_urls: tuple[str, ...] = ()
    video_urls: tuple[str, ...] = ()


class _ScriptCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.in_script = False
        self.scripts: list[str] = []
        self._current: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "script":
            self.in_script = True
            self._current = []

    def handle_data(self, data: str) -> None:
        if self.in_script:
            self._current.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self.in_script:
            self.scripts.append("".join(self._current))
            self.in_script = False
            self._current = []


def extract_xiaohongshu_urls(text: str) -> list[str]:
    urls: list[str] = []
    for raw_candidate in URL_PATTERN.findall(text):
        candidate = raw_candidate.rstrip(".,!;:)'\"")
        try:
            host = _validated_host(candidate)
        except ValueError:
            continue
        if host in ALLOWED_HOSTS and candidate not in urls:
            urls.append(candidate)
    return urls


def canonicalize_xiaohongshu_url(
    url: str,
    redirect_resolver: Callable[[str], Sequence[str]] | None = None,
) -> str:
    host = _validated_host(url)
    if host not in ALLOWED_HOSTS:
        raise ValueError("URL host is not an allowed Xiaohongshu host")

    chain = [url]
    if host in SHORT_LINK_HOSTS:
        if redirect_resolver is None:
            raise ValueError("Xiaohongshu short link requires an explicit redirect resolver")
        chain = list(redirect_resolver(url))
        if not chain or len(chain) > 6:
            raise ValueError("Unsafe Xiaohongshu redirect chain")

    for redirect_url in chain:
        try:
            redirect_host = _validated_host(redirect_url)
        except ValueError as exc:
            raise ValueError("Unsafe Xiaohongshu redirect target") from exc
        if redirect_host not in ALLOWED_HOSTS:
            raise ValueError("Xiaohongshu redirect left the allowed host set")

    final = urlsplit(chain[-1])
    if final.hostname in SHORT_LINK_HOSTS:
        raise ValueError("Xiaohongshu short link did not resolve to a content page")
    if not final.path or final.path == "/":
        raise ValueError("Xiaohongshu content URL has no item path")
    return urlunsplit(("https", final.netloc.lower(), final.path.rstrip("/"), "", ""))


def parse_initial_state(html: str) -> dict[str, Any]:
    collector = _ScriptCollector()
    collector.feed(html)
    marker = "window.__INITIAL_STATE__"
    for script in collector.scripts:
        marker_index = script.find(marker)
        if marker_index < 0:
            continue
        object_start = script.find("{", marker_index + len(marker))
        if object_start < 0:
            break
        try:
            payload = _balanced_object(script, object_start)
            parsed = json.loads(_replace_undefined_tokens(payload))
        except (ValueError, json.JSONDecodeError) as exc:
            raise ValueError("Malformed window.__INITIAL_STATE__ payload") from exc
        if not isinstance(parsed, dict):
            raise ValueError("Malformed window.__INITIAL_STATE__ payload")
        return parsed
    raise ValueError("window.__INITIAL_STATE__ payload not found")


def extract_xiaohongshu_record(
    html: str,
    *,
    canonical_url: str,
    captured_at: str,
    user_question: str | None = None,
) -> XiaohongshuExtraction:
    normalized_url = canonicalize_xiaohongshu_url(canonical_url)
    state = parse_initial_state(html)
    note = _find_note(state)
    note_id = str(note.get("noteId") or _post_id_from_url(normalized_url)).strip()
    safe_path_component(note_id, "Xiaohongshu note ID")

    image_urls = tuple(
        str(url)
        for item in _as_list(note.get("imageList"))
        if isinstance(item, dict)
        for url in [item.get("urlDefault") or item.get("urlPre") or item.get("url")]
        if isinstance(url, str) and url.startswith("https://")
    )
    video_urls = tuple(_extract_video_urls(note))

    if video_urls:
        content_type = "video"
        media = [ExternalMediaItem(kind="video")]
    elif image_urls:
        content_type = "image_text"
        media = [ExternalMediaItem(kind="image") for _ in image_urls]
    else:
        content_type = "text"
        media = []

    user = note.get("user") if isinstance(note.get("user"), dict) else {}
    tags = [
        str(item["name"]).strip()
        for item in _as_list(note.get("tagList"))
        if isinstance(item, dict) and str(item.get("name") or "").strip()
    ]
    record = ExternalContentRecord(
        source_id=f"xhs-{note_id}",
        platform="xiaohongshu",
        canonical_url=normalized_url,
        captured_at=captured_at,
        content_type=content_type,
        title=_optional_text(note.get("title")),
        description=_optional_text(note.get("desc")),
        author_display_name=_optional_text(user.get("nickname") or user.get("nickName")),
        tags=tags,
        media=media,
        extraction_status="complete" if note.get("desc") is not None else "partial",
        extraction_methods=["xiaohongshu_ssr"],
        user_question=user_question,
    )
    return XiaohongshuExtraction(record=record, image_urls=image_urls, video_urls=video_urls)


def _validated_host(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Only credential-free HTTPS URLs are allowed")
    host = parsed.hostname.rstrip(".").lower()
    if host == "localhost":
        raise ValueError("Local hosts are not allowed")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        if address.is_private or address.is_loopback or address.is_link_local or address.is_reserved:
            raise ValueError("Private or local addresses are not allowed")
    return host


def _balanced_object(source: str, start: int) -> str:
    depth = 0
    quote: str | None = None
    escaped = False
    for index in range(start, len(source)):
        char = source[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in {'"', "'"}:
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise ValueError("Unbalanced INITIAL_STATE object")


def _replace_undefined_tokens(payload: str) -> str:
    output: list[str] = []
    index = 0
    quote: str | None = None
    escaped = False
    while index < len(payload):
        char = payload[index]
        if quote:
            output.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            index += 1
            continue
        if char in {'"', "'"}:
            quote = char
            output.append(char)
            index += 1
            continue
        if payload.startswith("undefined", index):
            before = payload[index - 1] if index else ""
            after_index = index + len("undefined")
            after = payload[after_index] if after_index < len(payload) else ""
            if not (before.isalnum() or before in "_$") and not (after.isalnum() or after in "_$"):
                output.append("null")
                index = after_index
                continue
        output.append(char)
        index += 1
    return "".join(output)


def _find_note(state: dict[str, Any]) -> dict[str, Any]:
    note_root = state.get("note")
    detail_map = note_root.get("noteDetailMap") if isinstance(note_root, dict) else None
    if not isinstance(detail_map, dict):
        raise ValueError("Xiaohongshu noteDetailMap not found")
    for value in detail_map.values():
        if not isinstance(value, dict):
            continue
        note = value.get("note")
        if isinstance(note, dict):
            return note
    raise ValueError("Xiaohongshu note payload not found")


def _post_id_from_url(url: str) -> str:
    parts = [part for part in urlsplit(url).path.split("/") if part]
    if not parts:
        raise ValueError("Xiaohongshu post ID not found")
    return parts[-1]


def _extract_video_urls(note: dict[str, Any]) -> list[str]:
    video = note.get("video") if isinstance(note.get("video"), dict) else {}
    media = video.get("media") if isinstance(video.get("media"), dict) else {}
    stream = media.get("stream") if isinstance(media.get("stream"), dict) else {}
    urls: list[str] = []
    for codec in ("h264", "h265", "av1"):
        for item in _as_list(stream.get(codec)):
            if not isinstance(item, dict):
                continue
            url = item.get("masterUrl") or item.get("backupUrls")
            if isinstance(url, list):
                url = next((candidate for candidate in url if isinstance(candidate, str)), None)
            if isinstance(url, str) and url.startswith("https://") and url not in urls:
                urls.append(url)
    return urls


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
