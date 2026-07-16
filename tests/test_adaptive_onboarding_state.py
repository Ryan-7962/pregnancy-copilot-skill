import yaml

from pregnancy_copilot.data_init import initialize_data_dir
from pregnancy_copilot.onboarding_state import (
    DEFAULT_TUTORIAL_TOPICS,
    advance_onboarding_state,
    parse_message_controls,
    read_onboarding_state,
    select_tutorial_nudge,
)
from pregnancy_copilot.storage import PregnancyDataStore


def test_initialize_data_dir_creates_separate_onboarding_state(tmp_path):
    initialize_data_dir(tmp_path)

    path = tmp_path / "memory" / "onboarding_state.yaml"
    state = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert state["pregnancy_mode"] == "pending"
    assert state["tutorial_status"] == "in_progress"
    assert state["interaction_count"] == 0
    assert state["pending_topics"] == list(DEFAULT_TUTORIAL_TOPICS)
    assert state["preferences"]["prenatal_reminders_enabled"] is False


def test_tutorial_progresses_by_completed_topics_not_fixed_turn_count(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    state = read_onboarding_state(store)

    first = select_tutorial_nudge(state, profile_ready=False)
    assert first["topic"] == "welcome_and_scope"

    state = advance_onboarding_state(
        store,
        prompted_topic=first["topic"],
        interaction_timestamp="2026-07-15T10:00:00+08:00",
    )
    second = select_tutorial_nudge(state, profile_ready=False)
    assert second["topic"] == "minimum_profile"

    for index in range(12):
        state = advance_onboarding_state(
            store,
            interaction_timestamp=f"2026-07-15T10:{index + 1:02d}:00+08:00",
        )

    assert state["interaction_count"] == 13
    assert state["tutorial_status"] == "in_progress"
    assert "minimum_profile" in state["pending_topics"]


def test_profile_readiness_completes_minimum_profile_topic(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)

    state = advance_onboarding_state(store, profile_ready=True, pregnancy_mode="active")

    assert "minimum_profile" in state["completed_topics"]
    assert "minimum_profile" not in state["pending_topics"]
    assert state["pregnancy_mode"] == "active"


def test_tutorial_can_be_dismissed_and_resumed(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)

    dismissed = advance_onboarding_state(store, dismiss_tutorial=True)
    assert dismissed["tutorial_status"] == "dismissed"
    assert dismissed["tutorial_dismissed"] is True
    assert select_tutorial_nudge(dismissed, profile_ready=False) is None

    resumed = advance_onboarding_state(store, resume_tutorial=True)
    assert resumed["tutorial_status"] == "in_progress"
    assert resumed["tutorial_dismissed"] is False
    assert select_tutorial_nudge(resumed, profile_ready=False) is not None


def test_message_controls_are_conservative_and_message_scoped():
    assert parse_message_controls("这条不记录：我今天有点烦").record_mode == "no_record"
    assert parse_message_controls("仅本次回答，不要保存").record_mode == "no_record"
    assert parse_message_controls("仅本次").record_mode == "no_record"
    assert parse_message_controls("跳过教程，我直接问问题").dismiss_tutorial is True
    assert parse_message_controls("继续教程").resume_tutorial is True

    ordinary = parse_message_controls("不要忘记记录今天的体重")
    assert ordinary.record_mode == "default"
    assert ordinary.dismiss_tutorial is False


def test_each_tutorial_topic_is_emitted_at_most_once(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    emitted = []

    while True:
        state = read_onboarding_state(store)
        nudge = select_tutorial_nudge(state, profile_ready=True)
        if nudge is None:
            break
        emitted.append(nudge["topic"])
        advance_onboarding_state(
            store,
            prompted_topic=nudge["topic"],
            profile_ready=True,
            pregnancy_mode="active",
        )

    final_state = read_onboarding_state(store)
    assert len(emitted) == len(set(emitted))
    assert "minimum_profile" not in emitted
    assert final_state["tutorial_status"] == "complete"
    assert final_state["pending_topics"] == []
