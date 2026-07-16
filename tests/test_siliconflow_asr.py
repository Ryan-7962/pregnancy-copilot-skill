import json

import pytest

from pregnancy_copilot.external_content.asr import (
    ASRLimitError,
    ASRProviderError,
    SiliconFlowASR,
)


class FakeSender:
    def __init__(self, status=200, payload=None):
        self.status = status
        self.payload = payload or {"text": "synthetic transcript"}
        self.calls = []

    def __call__(self, url, headers, body, timeout):
        self.calls.append((url, headers, body, timeout))
        return self.status, json.dumps(self.payload).encode("utf-8")


def test_asr_sends_expected_multipart_fields_without_persisting_key(tmp_path):
    audio = tmp_path / "fixture.wav"
    audio.write_bytes(b"RIFF-synthetic-wave")
    sender = FakeSender()
    client = SiliconFlowASR(api_key="fixture-private-api-key", sender=sender)

    result = client.transcribe(audio, duration_seconds=12.0)

    assert result.text == "synthetic transcript"
    assert result.provider == "siliconflow"
    assert result.model == "FunAudioLLM/SenseVoiceSmall"
    url, headers, body, timeout = sender.calls[0]
    assert url == "https://api.siliconflow.cn/v1/audio/transcriptions"
    assert headers["Authorization"] == "Bearer fixture-private-api-key"
    assert b'name="model"' in body
    assert b"FunAudioLLM/SenseVoiceSmall" in body
    assert b'name="file"' in body
    assert b"RIFF-synthetic-wave" in body
    assert "fixture-private-api-key" not in repr(result)


def test_asr_supports_only_explicit_official_model_ids(tmp_path):
    with pytest.raises(ValueError, match="model"):
        SiliconFlowASR(api_key="key", model="unknown/model")

    client = SiliconFlowASR(
        api_key="key",
        model="TeleAI/TeleSpeechASR",
        sender=FakeSender(),
    )
    assert client.model == "TeleAI/TeleSpeechASR"


def test_asr_requires_key_and_enforces_provider_limits(tmp_path, monkeypatch):
    monkeypatch.delenv("SILICONFLOW_API_KEY", raising=False)
    with pytest.raises(ASRProviderError, match="SILICONFLOW_API_KEY"):
        SiliconFlowASR()

    oversized = tmp_path / "large.wav"
    oversized.write_bytes(b"x" * 11)
    client = SiliconFlowASR(api_key="fixture-secret", sender=FakeSender(), max_file_bytes=10)
    with pytest.raises(ASRLimitError, match="50MB|size"):
        client.transcribe(oversized, duration_seconds=1)
    with pytest.raises(ASRLimitError, match="one hour|duration"):
        client.transcribe(oversized, duration_seconds=3601)


def test_asr_provider_errors_do_not_leak_authorization(tmp_path):
    audio = tmp_path / "fixture.wav"
    audio.write_bytes(b"audio")
    client = SiliconFlowASR(
        api_key="fixture-private-api-key",
        sender=FakeSender(status=500, payload={"message": "internal failure"}),
    )

    with pytest.raises(ASRProviderError) as exc_info:
        client.transcribe(audio, duration_seconds=1)

    assert "fixture-private-api-key" not in str(exc_info.value)
