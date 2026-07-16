from pathlib import Path

import pytest

from pregnancy_copilot.external_content.media import (
    MediaPreparationError,
    cleanup_temporary_media,
    prepare_audio_with_ffmpeg,
    transcription_decision,
)


@pytest.mark.parametrize(
    ("policy", "consented", "expected"),
    [
        ("ask", False, "consent_required"),
        ("ask", True, "transcribe"),
        ("always", False, "transcribe"),
        ("never", True, "skip"),
    ],
)
def test_transcription_policy(policy, consented, expected):
    assert transcription_decision(policy, user_consented=consented) == expected


def test_transcription_policy_rejects_unknown_value():
    with pytest.raises(ValueError, match="policy"):
        transcription_decision("sometimes", user_consented=True)


def test_prepare_audio_uses_argument_array_and_fixed_audio_shape(tmp_path):
    source = tmp_path / "source video.mp4"
    output = tmp_path / "audio.wav"
    source.write_bytes(b"synthetic-video")
    calls = []

    def runner(args, **kwargs):
        calls.append((args, kwargs))
        Path(args[-1]).write_bytes(b"synthetic-wav")

    result = prepare_audio_with_ffmpeg(
        source,
        output,
        runner=runner,
        ffmpeg_path="/usr/local/bin/ffmpeg",
    )

    assert result == output
    args, kwargs = calls[0]
    assert isinstance(args, list)
    assert args[0] == "/usr/local/bin/ffmpeg"
    assert args[args.index("-ar") + 1] == "16000"
    assert args[args.index("-ac") + 1] == "1"
    assert kwargs["check"] is True
    assert kwargs["timeout"] > 0


def test_prepare_audio_handles_missing_ffmpeg_and_oversized_output(tmp_path):
    source = tmp_path / "video.mp4"
    output = tmp_path / "audio.wav"
    source.write_bytes(b"video")

    with pytest.raises(MediaPreparationError, match="ffmpeg"):
        prepare_audio_with_ffmpeg(source, output, locator=lambda _name: None)

    def oversized_runner(args, **kwargs):
        Path(args[-1]).write_bytes(b"x" * 11)

    with pytest.raises(MediaPreparationError, match="size"):
        prepare_audio_with_ffmpeg(
            source,
            output,
            runner=oversized_runner,
            ffmpeg_path="ffmpeg",
            max_output_bytes=10,
        )
    assert not output.exists()


def test_cleanup_deletes_temporary_media_unless_retained(tmp_path):
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.wav"
    first.write_bytes(b"first")
    second.write_bytes(b"second")

    cleanup_temporary_media([first, second], retain=False)
    assert not first.exists()
    assert not second.exists()

    first.write_bytes(b"first")
    cleanup_temporary_media([first], retain=True)
    assert first.exists()
