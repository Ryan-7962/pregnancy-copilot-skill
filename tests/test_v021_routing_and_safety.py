from pregnancy_copilot.host_runtime import HostMessageRequest, process_host_message
from pregnancy_copilot.triage import LLMTriageAdvisor, triage_message
from tests.helpers import make_profile_ready


def test_pregnancy_workspace_context_is_not_bypassed_by_missing_keywords(tmp_path):
    make_profile_ready(tmp_path)

    for index, text in enumerate(["孕期能吃生鱼片吗？", "怀孕可以坐飞机吗？"]):
        result = process_host_message(
            HostMessageRequest(
                text=text,
                sender_id="pregnant-user",
                conversation_id="pregnancy-window",
                channel="agent_default",
                timestamp=f"2026-07-15T10:0{index}:00+08:00",
            ),
            data_root=tmp_path,
        )

        assert result.handled is True
        assert result.context_package is not None
        assert result.host_action["use_context_package"] is True
        assert result.risk_level == "not_applicable"
        assert result.triage_required is False


def test_general_chat_gets_context_without_forcing_triage_or_medical_event(tmp_path):
    make_profile_ready(tmp_path)

    result = process_host_message(
        HostMessageRequest(
            text="推荐一首歌",
            sender_id="pregnant-user",
            conversation_id="pregnancy-window",
            channel="agent_default",
            timestamp="2026-07-15T10:10:00+08:00",
        ),
        data_root=tmp_path,
    )

    assert result.handled is True
    assert result.intent == "pregnancy_context"
    assert result.triage_required is False
    assert result.risk_level == "not_applicable"
    assert result.event is None
    assert result.context_package is not None
    assert result.context_package["semantic_routing_contract"]["performed_by"] == "host_llm"
    assert result.context_package["semantic_routing_contract"]["risk_label_policy"] == "medical_relevance_only"
    assert result.context_package["memory_write_policy"]["append_structured_event"] is False
    assert result.context_package["memory_write_policy"]["host_may_write_after_semantic_decision"] is True
    assert not (tmp_path / "events" / "events.jsonl").exists()


def test_negated_past_does_not_hide_current_bleeding():
    assert triage_message("之前没有出血，现在出血了").risk_level == "red"
    assert triage_message("没有明显出血，但刚才又有少量出血").risk_level != "green"
    assert triage_message("一直没有出血").risk_level != "red"


def test_reduced_fetal_movement_variant_is_in_deterministic_safety_floor():
    result = triage_message("胎动比平时少")

    assert result.risk_level == "red"
    assert "胎动异常" in result.red_flags_detected


def test_emergency_before_profile_never_uses_template_medical_facts(tmp_path):
    result = process_host_message(
        HostMessageRequest(
            text="现在有鲜红色出血",
            sender_id="new-pregnant-user",
            conversation_id="new-pregnancy-window",
            channel="agent_default",
            timestamp="2026-07-15T10:20:00+08:00",
        ),
        data_root=tmp_path,
    )

    assert result.risk_level == "red"
    assert result.event is not None
    assert result.event["gestational_age"] in {None, "unknown"}
    assert result.context_package is not None
    assert "W20+0" not in result.context_package["context_markdown"]
    assert "示例医院" not in result.context_package["context_markdown"]
    assert result.context_package["profile_readiness"]["status"] == "needs_review"


class FailingProvider:
    def generate(self, prompt):
        raise RuntimeError("host model unavailable")


class RefusingProvider:
    def generate(self, prompt):
        return "抱歉，我无法完成这个请求。"


def test_triage_falls_back_safely_when_host_llm_raises():
    result = triage_message("现在有鲜红色出血", advisor=LLMTriageAdvisor(FailingProvider()))

    assert result.risk_level == "red"
    assert "阴道流血" in result.red_flags_detected


def test_triage_does_not_claim_semantic_assessment_for_llm_refusal():
    result = triage_message("今天肚子有点紧，休息后好了", advisor=LLMTriageAdvisor(RefusingProvider()))

    assert result.risk_level == "green"
    assert "LLM" not in result.reason


def test_final_response_falls_back_when_host_llm_raises(tmp_path):
    make_profile_ready(tmp_path)

    result = process_host_message(
        HostMessageRequest(
            text="今天肚子有点紧，休息后好了",
            sender_id="pregnant-user",
            conversation_id="pregnancy-window",
            channel="agent_default",
            timestamp="2026-07-15T12:00:00+08:00",
        ),
        data_root=tmp_path,
        response_provider=FailingProvider(),
    )

    assert result.risk_level == "green"
    assert "风险分级" in result.reply_text
