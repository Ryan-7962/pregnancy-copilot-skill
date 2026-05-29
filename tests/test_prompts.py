from pregnancy_copilot.models import TriageResult
from pregnancy_copilot.prompts import PromptBuilder, ResponseWriter


def test_prompt_builder_creates_pregnancy_qa_prompt_with_context_and_safety_rules():
    prompt = PromptBuilder().build_pregnancy_qa_prompt(
        context="# Current Context\n\nW8+2",
        user_message="今天肚子有点紧，休息后好了",
        risk_level="green",
    )

    assert "Pregnancy Copilot Skill" in prompt
    assert "W8+2" in prompt
    assert "今天肚子有点紧" in prompt
    assert "风险级别：green" in prompt
    assert "不替代医生诊断" in prompt
    assert "不得编造" in prompt
    assert "model" not in prompt.lower()


def test_response_writer_builds_safety_bounded_triage_reply():
    triage = TriageResult(
        risk_level="red",
        reason="检测到阴道流血",
        red_flags_detected=["阴道流血"],
        recommended_action="尽快联系产科医生或就医。",
        must_include_medical_disclaimer=True,
        must_recommend_doctor_contact=True,
        doctor_question_candidates=["是否需要立即去急诊？"],
    )

    reply = ResponseWriter().write_triage_reply(triage)

    assert "风险分级：红色" in reply
    assert "不替代医生" in reply
    assert "尽快联系产科医生" in reply
    assert "是否需要立即去急诊？" in reply
