from __future__ import annotations

from dataclasses import dataclass
import json
import mimetypes
import os
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4


ASR_ENDPOINT = "https://api.siliconflow.cn/v1/audio/transcriptions"
SUPPORTED_MODELS = {"FunAudioLLM/SenseVoiceSmall", "TeleAI/TeleSpeechASR"}
DEFAULT_MODEL = "FunAudioLLM/SenseVoiceSmall"
PROVIDER_MAX_BYTES = 50 * 1024 * 1024
PROVIDER_MAX_DURATION_SECONDS = 3600.0


class ASRProviderError(RuntimeError):
    pass


class ASRLimitError(ASRProviderError):
    pass


@dataclass(frozen=True)
class ASRResult:
    text: str
    provider: str
    model: str


class SiliconFlowASR:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        sender: Callable[[str, dict[str, str], bytes, float], tuple[int, bytes]] | None = None,
        timeout_seconds: float = 120.0,
        max_file_bytes: int = PROVIDER_MAX_BYTES,
    ) -> None:
        if model not in SUPPORTED_MODELS:
            raise ValueError(f"Unsupported SiliconFlow ASR model: {model!r}")
        key = (api_key or os.environ.get("SILICONFLOW_API_KEY") or "").strip()
        if not key:
            raise ASRProviderError("SILICONFLOW_API_KEY is required for optional video transcription")
        self._api_key = key
        self.model = model
        self.sender = sender or _default_sender
        self.timeout_seconds = timeout_seconds
        self.max_file_bytes = min(max_file_bytes, PROVIDER_MAX_BYTES)

    def transcribe(self, audio_path: str | Path, *, duration_seconds: float | None = None) -> ASRResult:
        if duration_seconds is not None and duration_seconds > PROVIDER_MAX_DURATION_SECONDS:
            raise ASRLimitError("Audio duration exceeds the provider limit of one hour")
        path = Path(audio_path)
        if not path.is_file():
            raise ASRProviderError("Prepared audio file is not available")
        if path.stat().st_size > self.max_file_bytes:
            raise ASRLimitError("Audio size exceeds the provider 50MB size limit")
        boundary = f"pregnancy-copilot-{uuid4().hex}"
        body = _multipart_body(path, self.model, boundary)
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
        }
        try:
            status, response_body = self.sender(
                ASR_ENDPOINT,
                headers,
                body,
                self.timeout_seconds,
            )
        except Exception as exc:
            raise ASRProviderError("SiliconFlow ASR request failed") from exc
        if status < 200 or status >= 300:
            raise ASRProviderError(f"SiliconFlow ASR returned HTTP status {status}")
        try:
            payload = json.loads(response_body.decode("utf-8"))
            text = str(payload["text"]).strip()
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
            raise ASRProviderError("SiliconFlow ASR returned an invalid response") from exc
        if not text:
            raise ASRProviderError("SiliconFlow ASR returned an empty transcript")
        return ASRResult(text=text, provider="siliconflow", model=self.model)


def _multipart_body(path: Path, model: str, boundary: str) -> bytes:
    delimiter = f"--{boundary}\r\n".encode("ascii")
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return b"".join(
        [
            delimiter,
            b'Content-Disposition: form-data; name="model"\r\n\r\n',
            model.encode("utf-8"),
            b"\r\n",
            delimiter,
            f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'.encode("utf-8"),
            f"Content-Type: {content_type}\r\n\r\n".encode("ascii"),
            path.read_bytes(),
            b"\r\n",
            f"--{boundary}--\r\n".encode("ascii"),
        ]
    )


def _default_sender(url: str, headers: dict[str, str], body: bytes, timeout: float) -> tuple[int, bytes]:
    request = Request(url, data=body, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=timeout) as response:
            return int(response.status), response.read()
    except HTTPError as exc:
        return int(exc.code), exc.read()
    except URLError as exc:
        raise ASRProviderError("SiliconFlow ASR network request failed") from exc
