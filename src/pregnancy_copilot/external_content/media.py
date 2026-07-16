from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
from typing import Callable, Iterable


TRANSCRIPTION_POLICIES = {"ask", "always", "never"}


class MediaPreparationError(RuntimeError):
    pass


def transcription_decision(policy: str, *, user_consented: bool) -> str:
    if policy not in TRANSCRIPTION_POLICIES:
        raise ValueError(f"Unsupported video transcription policy: {policy!r}")
    if policy == "never":
        return "skip"
    if policy == "always" or user_consented:
        return "transcribe"
    return "consent_required"


def prepare_audio_with_ffmpeg(
    source_video: str | Path,
    output_audio: str | Path,
    *,
    runner: Callable = subprocess.run,
    locator: Callable[[str], str | None] = shutil.which,
    ffmpeg_path: str | None = None,
    timeout_seconds: float = 120.0,
    max_output_bytes: int = 50 * 1024 * 1024,
) -> Path:
    source = Path(source_video)
    output = Path(output_audio)
    if not source.is_file():
        raise MediaPreparationError("Source video is not available")
    executable = ffmpeg_path or locator("ffmpeg")
    if not executable:
        raise MediaPreparationError("ffmpeg is required for video transcription")
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        executable,
        "-nostdin",
        "-y",
        "-i",
        str(source),
        "-vn",
        "-ar",
        "16000",
        "-ac",
        "1",
        "-c:a",
        "pcm_s16le",
        str(output),
    ]
    try:
        runner(
            command,
            check=True,
            capture_output=True,
            timeout=timeout_seconds,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        output.unlink(missing_ok=True)
        raise MediaPreparationError("ffmpeg could not prepare audio") from exc
    if not output.is_file():
        raise MediaPreparationError("ffmpeg did not produce an audio file")
    if output.stat().st_size > max_output_bytes:
        output.unlink(missing_ok=True)
        raise MediaPreparationError("Prepared audio exceeded the configured size limit")
    return output


def cleanup_temporary_media(paths: Iterable[str | Path], *, retain: bool) -> None:
    if retain:
        return
    for value in paths:
        path = Path(value)
        if path.is_file() or path.is_symlink():
            path.unlink(missing_ok=True)
