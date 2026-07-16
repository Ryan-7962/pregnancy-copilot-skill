from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
from typing import Any
from urllib.parse import urlsplit

from pregnancy_copilot.storage import safe_iso_date, safe_path_component


ALLOWED_CONTENT_TYPES = {"image_text", "video", "text", "unknown"}
ALLOWED_EXTRACTION_STATUSES = {"complete", "partial", "credentials_required", "failed"}


@dataclass(frozen=True)
class ExternalMediaItem:
    kind: str
    relative_path: str | None = None
    extraction_status: str = "pending_host_analysis"

    def __post_init__(self) -> None:
        if self.kind not in {"image", "video", "audio"}:
            raise ValueError(f"Unsupported media kind: {self.kind!r}")
        if self.relative_path:
            normalized = self.relative_path.replace("\\", "/")
            if not normalized.startswith("external_sources/media/") or ".." in normalized.split("/"):
                raise ValueError(f"Unsafe media relative_path: {self.relative_path!r}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "relative_path": self.relative_path,
            "extraction_status": self.extraction_status,
        }


@dataclass(frozen=True)
class ExternalContentRecord:
    source_id: str
    platform: str
    canonical_url: str
    captured_at: str
    content_type: str
    title: str | None = None
    description: str | None = None
    author_display_name: str | None = None
    author_identity_status: str = "unverified"
    tags: list[str] = field(default_factory=list)
    media: list[ExternalMediaItem] = field(default_factory=list)
    extraction_status: str = "partial"
    extraction_methods: list[str] = field(default_factory=list)
    source_confidence: str = "social_media_unverified"
    user_question: str | None = None
    topic_tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        safe_path_component(self.source_id, "source_id")
        safe_iso_date(self.captured_at)
        parsed = urlsplit(self.canonical_url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.query or parsed.fragment or parsed.username:
            raise ValueError("canonical_url must be a query-free HTTPS URL")
        if self.content_type not in ALLOWED_CONTENT_TYPES:
            raise ValueError(f"Unsupported content_type: {self.content_type!r}")
        if self.extraction_status not in ALLOWED_EXTRACTION_STATUSES:
            raise ValueError(f"Unsupported extraction_status: {self.extraction_status!r}")
        if self.source_confidence != "social_media_unverified":
            raise ValueError("External social content must remain social_media_unverified")

    @property
    def content_hash(self) -> str:
        payload = self.to_dict()
        payload.pop("captured_at", None)
        payload.pop("user_question", None)
        return sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "platform": self.platform,
            "canonical_url": self.canonical_url,
            "captured_at": self.captured_at,
            "content_type": self.content_type,
            "title": self.title,
            "description": self.description,
            "author_display_name": self.author_display_name,
            "author_identity_status": self.author_identity_status,
            "tags": list(self.tags),
            "media": [item.to_dict() for item in self.media],
            "extraction_status": self.extraction_status,
            "extraction_methods": list(self.extraction_methods),
            "source_confidence": self.source_confidence,
            "user_question": self.user_question,
            "topic_tags": list(self.topic_tags),
        }
