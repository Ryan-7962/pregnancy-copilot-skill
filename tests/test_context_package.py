from scripts.init_data_dir import initialize_data_dir
from pregnancy_copilot.context_package import build_host_context_package
from pregnancy_copilot.host_runtime import HostMessageRequest, process_host_message
from pregnancy_copilot.medical_state import record_medical_observation
from pregnancy_copilot.storage import PregnancyDataStore
from scripts.process_host_message import run_host_message
from tests.helpers import make_profile_ready


def test_context_package_prioritizes_current_medical_state_for_host_llm(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    record_medical_observation(
        store,
        {
            "observation_id": "obs-placenta-old",
            "metric_key": "placenta_position",
            "display_name": "胎盘位置",
            "value": "距宫颈内口 23mm",
            "measured_at": "2026-03-26",
            "status": "watch",
        },
    )
    record_medical_observation(
        store,
        {
            "observation_id": "obs-placenta-new",
            "metric_key": "placenta_position",
            "display_name": "胎盘位置",
            "value": "宫底后壁",
            "measured_at": "2026-05-08",
            "status": "resolved",
            "interpretation": "旧 23mm 状态已被刷新。",
        },
    )

    package = build_host_context_package(
        store=store,
        user_message="胎盘现在还有低置风险吗？",
        intent="report_review",
        channel="hermes",
    )

    assert package["schema_version"] == "0.1"
    assert package["runtime_role"] == "host_llm_context"
    assert "宿主大模型负责医学审计" in package["system_prompt"]
    assert "current_medical_state.yaml" in package["system_prompt"]
    assert "调用写入工具成功前" in package["system_prompt"]
    assert "已录入" in package["system_prompt"]
    assert "不知道" in package["system_prompt"]
    assert "要求用户补充" in package["system_prompt"]
    assert package["current_medical_state"]["metrics"]["placenta_position"]["current"]["value"] == "宫底后壁"
    assert package["current_medical_state"]["metrics"]["placenta_position"]["previous_values"][0]["value"] == "距宫颈内口 23mm"
    assert "旧值已被更新，不应作为当前判断依据" in package["context_markdown"]
    assert "不要把 previous_values 当作当前事实" in package["safety_floor"][0]
    assert any("写入工具已经成功返回" in item for item in package["safety_floor"])
    assert package["memory_write_policy"]["preserve_raw_message"] is True
    assert package["memory_write_policy"]["do_not_claim_memory_write_without_tool_success"] is True
    assert package["memory_write_policy"]["update_current_medical_state_after_new_observations"] == "only_after_explicit_tool_success"
    assert package["output_contract"]["do_not_claim_new_data_recorded_unless_tool_succeeded"] is True
    assert package["output_contract"]["say_unknown_or_ask_for_more_information_when_insufficient"] is True


def test_host_runtime_returns_context_package_for_handled_pregnancy_message(tmp_path):
    make_profile_ready(tmp_path)
    result = process_host_message(
        HostMessageRequest(
            text="这个 B 超数据是什么意思",
            sender_id="pregnant-user",
            sender_role="pregnant_user",
            conversation_id="pregnancy-window",
            channel="hermes",
            timestamp="2026-05-16T09:00:00+08:00",
        ),
        data_root=tmp_path,
    )

    assert result.handled is True
    assert result.context_package is not None
    assert result.context_package["user_message"] == "这个 B 超数据是什么意思"
    assert result.context_package["intent"] == "report_review"
    assert "当前有效医学状态" in result.context_package["context_markdown"]
    assert result.context_package["memory_write_policy"]["append_structured_event"] is True


def test_host_runtime_keeps_minimal_context_for_general_chat_without_triage(tmp_path):
    make_profile_ready(tmp_path)
    result = process_host_message(
        HostMessageRequest(
            text="推荐一首歌",
            sender_id="pregnant-user",
            conversation_id="pregnancy-window",
            channel="hermes",
            timestamp="2026-05-16T09:01:00+08:00",
        ),
        data_root=tmp_path,
    )

    assert result.handled is True
    assert result.intent == "pregnancy_context"
    assert result.context_package is not None
    assert result.triage_required is False
    assert result.risk_level == "not_applicable"


def test_process_host_message_script_includes_context_package(tmp_path):
    make_profile_ready(tmp_path)
    result = run_host_message(
        data_root=tmp_path,
        text="今天肚子有点紧，休息后好了",
        sender_id="pregnant-user",
        conversation_id="pregnancy-window",
        channel="hermes",
        timestamp="2026-05-16T09:02:00+08:00",
    )

    assert result["context_package"]["intent"] == "medical_triage"
    assert "宿主大模型负责医学审计" in result["context_package"]["system_prompt"]
