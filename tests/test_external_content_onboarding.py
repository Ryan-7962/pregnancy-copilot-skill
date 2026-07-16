from pregnancy_copilot.onboarding_state import (
    DEFAULT_TUTORIAL_TOPICS,
    advance_onboarding_state,
    default_onboarding_state,
    parse_message_controls,
    select_tutorial_nudge,
)
from pregnancy_copilot.storage import PregnancyDataStore


def test_external_content_is_optional_last_tutorial_topic():
    assert DEFAULT_TUTORIAL_TOPICS[-1] == "external_content_audit"
    state = default_onboarding_state()
    state["completed_topics"] = list(DEFAULT_TUTORIAL_TOPICS[:-1])
    state["pending_topics"] = ["external_content_audit"]

    nudge = select_tutorial_nudge(state, profile_ready=True)

    assert nudge["topic"] == "external_content_audit"
    assert "小红书" in nudge["text"]
    assert "个人经验" in nudge["text"]


def test_external_preferences_default_and_can_be_changed_by_chat(tmp_path):
    defaults = default_onboarding_state()["preferences"]
    assert defaults["xhs_video_transcription"] == "ask"
    assert defaults["external_media_retention"] is False

    controls = parse_message_controls("小红书视频以后都转写，并保留外部内容原图")
    assert controls.xhs_video_transcription == "always"
    assert controls.external_media_retention is True
    state = advance_onboarding_state(
        PregnancyDataStore(tmp_path),
        preference_updates={
            "xhs_video_transcription": controls.xhs_video_transcription,
            "external_media_retention": controls.external_media_retention,
        },
    )
    assert state["preferences"]["xhs_video_transcription"] == "always"
    assert state["preferences"]["external_media_retention"] is True


def test_external_preferences_support_ask_never_and_delete_media():
    assert parse_message_controls("小红书视频每次先问我").xhs_video_transcription == "ask"
    assert parse_message_controls("不要转写小红书视频").xhs_video_transcription == "never"
    assert parse_message_controls("外部内容识别后删除原图").external_media_retention is False
