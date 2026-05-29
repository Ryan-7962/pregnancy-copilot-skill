from pregnancy_copilot.models import TriageResult
from pregnancy_copilot.triage import LLMTriageAdvisor, triage_message


class StaticAdvisor:
    def __init__(self, result):
        self.result = result

    def assess(self, text, rule_result):
        return self.result


class StaticProvider:
    def __init__(self, response):
        self.response = response
        self.prompts = []

    def generate(self, prompt):
        self.prompts.append(prompt)
        return self.response


def test_green_common_message_after_rest():
    result = triage_message("今天肚子有点紧，休息后好了，没有流血也没有流水")
    assert result.risk_level == "green"
    assert result.must_include_medical_disclaimer is True
    assert result.must_recommend_doctor_contact is False


def test_red_flag_bleeding():
    result = triage_message("我今天有点流血")
    assert result.risk_level == "red"
    assert "阴道流血" in result.red_flags_detected
    assert result.must_recommend_doctor_contact is True


def test_red_flag_decreased_fetal_movement():
    result = triage_message("宝宝今天动得明显少了")
    assert result.risk_level == "red"
    assert "胎动异常" in result.red_flags_detected


def test_red_flag_headache_with_vision_change():
    result = triage_message("我头痛很厉害还眼花")
    assert result.risk_level == "red"
    assert "严重头痛或视力变化" in result.red_flags_detected


def test_yellow_report_question_needs_doctor_confirmation():
    result = triage_message("这个 B 超数据是什么意思")
    assert result.risk_level == "yellow"
    assert result.must_include_medical_disclaimer is True
    assert result.doctor_question_candidates


def test_semantic_advisor_can_escalate_without_keyword_match():
    advisor = StaticAdvisor(
        TriageResult(
            risk_level="red",
            reason="语义判断可能是破水或异常分泌物，需要立即联系医生。",
            red_flags_detected=["语义红旗"],
            recommended_action="请尽快联系产科医生或产科急诊。",
            must_include_medical_disclaimer=True,
            must_recommend_doctor_contact=True,
        )
    )

    result = triage_message("下面突然湿了一大片，不确定是不是漏尿", advisor=advisor)

    assert result.risk_level == "red"
    assert "语义红旗" in result.red_flags_detected


def test_semantic_advisor_cannot_downgrade_rule_red():
    advisor = StaticAdvisor(
        TriageResult(
            risk_level="green",
            reason="错误降级",
            must_include_medical_disclaimer=False,
            must_recommend_doctor_contact=False,
        )
    )

    result = triage_message("我今天有点流血", advisor=advisor)

    assert result.risk_level == "red"
    assert "阴道流血" in result.red_flags_detected


def test_llm_triage_advisor_parses_json_and_builds_safety_prompt():
    provider = StaticProvider(
        """
        {
          "risk_level": "yellow",
          "reason": "语义上需要补充孕周和持续时间。",
          "red_flags_detected": [],
          "missing_questions": ["现在孕周是多少？", "持续了多久？"],
          "recommended_action": "记录细节，必要时联系医生。",
          "doctor_question_candidates": ["是否需要提前就诊？"]
        }
        """
    )
    advisor = LLMTriageAdvisor(provider)

    result = triage_message("今天不太对劲，但说不上来", advisor=advisor)

    assert result.risk_level == "yellow"
    assert "现在孕周是多少？" in result.missing_questions
    assert "红黄绿" in provider.prompts[0]


def test_llm_triage_advisor_ignores_invalid_output():
    provider = StaticProvider("not json")
    advisor = LLMTriageAdvisor(provider)

    result = triage_message("今天肚子有点紧，休息后好了", advisor=advisor)

    assert result.risk_level == "green"
