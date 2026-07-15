from __future__ import annotations

import json
import re
from typing import Protocol

from .models import TriageResult


RISK_ORDER = {"green": 0, "yellow": 1, "red": 2}

RED_FLAG_KEYWORDS = {
    "阴道流血": ["流血", "出血", "见红"],
    "疑似破水": ["流水", "破水", "水一样"],
    "胎动异常": ["胎动明显减少", "胎动明显少", "动得明显少", "胎动少了很多", "胎动比平时少", "胎动停止", "不动了"],
    "严重腹痛": ["剧烈腹痛", "持续腹痛", "痛得受不了"],
    "严重头痛或视力变化": ["严重头痛", "头痛很厉害", "眼花", "视力模糊"],
    "胸痛或呼吸困难": ["胸痛", "喘不上气", "呼吸困难"],
    "晕厥": ["晕倒", "快晕了", "昏厥"],
    "自伤想法": ["想伤害自己", "不想活", "伤害宝宝"],
}


MEDICAL_TOPIC_KEYWORDS = [
    "肚子",
    "肚皮",
    "腹痛",
    "宫缩",
    "胎动",
    "B 超",
    "b 超",
    "报告",
    "用药",
    "药",
    "血糖",
    "血压",
    "头晕",
    "低血压",
    "平躺",
    "仰卧",
]


def _is_negated_at(text: str, index: int) -> bool:
    prefix = text[:index]
    clause_prefix = re.split(r"[，,。；;!！?？\n]|但是|但|现在|后来|刚才|又", prefix)[-1]
    if any(marker in clause_prefix for marker in ["不是没有", "并非没有", "不能说没有"]):
        return False
    return bool(re.search(r"(?:没有|不曾|并无|没|无|未)[^，,。；;!！?？\n]{0,6}$", clause_prefix))


def _contains_keyword(text: str, keyword: str) -> bool:
    return any(not _is_negated_at(text, match.start()) for match in re.finditer(re.escape(keyword), text))


class TriageAdvisor(Protocol):
    def assess(self, text: str, rule_result: TriageResult) -> TriageResult | None:
        pass


class LLMTriageAdvisor:
    def __init__(self, provider):
        self.provider = provider

    def assess(self, text: str, rule_result: TriageResult) -> TriageResult | None:
        prompt = build_llm_triage_prompt(text, rule_result)
        try:
            raw = self.provider.generate(prompt)
        except Exception:
            return None
        payload = parse_json_object(raw)
        if not payload:
            return None
        risk_level = payload.get("risk_level")
        if risk_level not in RISK_ORDER:
            return None
        return TriageResult(
            risk_level=risk_level,
            reason=str(payload.get("reason") or "LLM 语义分级补充。"),
            red_flags_detected=list(payload.get("red_flags_detected") or []),
            missing_questions=list(payload.get("missing_questions") or []),
            recommended_action=str(payload.get("recommended_action") or ""),
            doctor_question_candidates=list(payload.get("doctor_question_candidates") or []),
            must_include_medical_disclaimer=True,
            must_recommend_doctor_contact=risk_level in {"yellow", "red"},
        )


def triage_message(text: str, advisor: TriageAdvisor | None = None) -> TriageResult:
    rule_result = rule_triage_message(text)
    if not advisor:
        return rule_result
    semantic_result = advisor.assess(text, rule_result)
    if not semantic_result:
        return rule_result
    return merge_triage_results(rule_result, semantic_result)


def rule_triage_message(text: str) -> TriageResult:
    detected = []
    for flag, keywords in RED_FLAG_KEYWORDS.items():
        if any(_contains_keyword(text, k) for k in keywords):
            detected.append(flag)

    if detected:
        return TriageResult(
            risk_level="red",
            reason="检测到孕期红旗症状关键词，需要优先联系医生或就医。",
            red_flags_detected=detected,
            recommended_action="请尽快联系产科医生、产科急诊或医院急诊；如情况紧急，请拨打当地急救电话。",
            must_include_medical_disclaimer=True,
            must_recommend_doctor_contact=True,
        )

    yellow_keywords = ["持续", "加重", "反复", "异常", "很担心", "睡不着", "血糖高", "血压高", "B 超", "b 超", "报告"]
    if any(k in text for k in yellow_keywords):
        return TriageResult(
            risk_level="yellow",
            reason="描述中存在持续、加重或需要医生确认的线索。",
            recommended_action="建议记录症状，并尽快联系医生或作为下次产检重点询问。",
            doctor_question_candidates=["这项情况或报告数据是否需要进一步检查或复查？"],
            must_include_medical_disclaimer=True,
            must_recommend_doctor_contact=True,
        )

    is_medical_topic = any(keyword in text for keyword in MEDICAL_TOPIC_KEYWORDS)
    return TriageResult(
        risk_level="green",
        reason="未检测到明确红旗症状；仍需结合孕周、历史和补充信息判断。",
        recommended_action="可先记录频率、持续时间、是否休息后缓解，并观察变化。",
        must_include_medical_disclaimer=is_medical_topic,
        must_recommend_doctor_contact=False,
    )


def merge_triage_results(rule_result: TriageResult, semantic_result: TriageResult) -> TriageResult:
    if RISK_ORDER[semantic_result.risk_level] < RISK_ORDER[rule_result.risk_level]:
        return rule_result
    if RISK_ORDER[semantic_result.risk_level] == RISK_ORDER[rule_result.risk_level]:
        return TriageResult(
            risk_level=rule_result.risk_level,
            reason=combine_text(rule_result.reason, semantic_result.reason),
            red_flags_detected=dedupe(rule_result.red_flags_detected + semantic_result.red_flags_detected),
            missing_questions=dedupe(rule_result.missing_questions + semantic_result.missing_questions),
            recommended_action=semantic_result.recommended_action or rule_result.recommended_action,
            doctor_question_candidates=dedupe(
                rule_result.doctor_question_candidates + semantic_result.doctor_question_candidates
            ),
            must_include_medical_disclaimer=rule_result.must_include_medical_disclaimer
            or semantic_result.must_include_medical_disclaimer,
            must_recommend_doctor_contact=rule_result.must_recommend_doctor_contact
            or semantic_result.must_recommend_doctor_contact,
        )
    return semantic_result


def build_llm_triage_prompt(text: str, rule_result: TriageResult) -> str:
    return "\n".join(
        [
            "请对孕期用户消息进行红黄绿语义分级。",
            "",
            "规则层初判：",
            json.dumps(
                {
                    "risk_level": rule_result.risk_level,
                    "reason": rule_result.reason,
                    "red_flags_detected": rule_result.red_flags_detected,
                },
                ensure_ascii=False,
            ),
            "",
            "用户消息：",
            text,
            "",
            "输出 JSON，字段为 risk_level, reason, red_flags_detected, missing_questions, recommended_action, doctor_question_candidates。",
            "要求：不替代医生诊断；红色表示建议立即联系产科医生/急诊；黄色表示建议联系医生或产检重点确认；绿色表示可记录观察。",
        ]
    )


def parse_json_object(text: str) -> dict | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None


def dedupe(items: list[str]) -> list[str]:
    result = []
    seen = set()
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def combine_text(first: str, second: str) -> str:
    if not second or second == first:
        return first
    return f"{first}；语义补充：{second}"
