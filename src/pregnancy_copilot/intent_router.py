from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IntentClassification:
    intent: str
    handled_by_skill: bool
    triage_required: bool
    write_to_memory: bool
    reason: str


MEDICAL_TRIAGE_KEYWORDS = [
    "出血",
    "流血",
    "见红",
    "破水",
    "流水",
    "宫缩",
    "肚子",
    "肚子紧",
    "腹痛",
    "肚子痛",
    "肚子疼",
    "胎动",
    "头痛",
    "头晕",
    "眼花",
    "胸痛",
    "呼吸困难",
    "晕倒",
    "低血压",
    "平躺",
    "仰卧",
    "发烧",
    "发热",
    "漏尿",
    "湿了一大片",
    "下面湿",
    "内裤湿",
]

MEDICATION_KEYWORDS = ["用药", "吃药", "药", "剂量", "叶酸", "钙片", "止痛药", "抗生素"]

REPORT_KEYWORDS = ["B 超", "b 超", "B超", "b超", "报告", "化验", "检查单", "胎心", "唐筛", "糖耐", "NT"]
REPORT_TRIAGE_KEYWORDS = ["异常", "偏高", "偏低", "高风险", "临界", "需要复查", "进一步检查", "医生建议尽快", "医生说异常"]

PREGNANCY_LOG_KEYWORDS = [
    "体重",
    "血压",
    "血糖",
    "早餐",
    "午餐",
    "晚餐",
    "饮食",
    "吃了",
    "运动",
    "散步",
    "睡眠",
    "睡了",
]

MOOD_KEYWORDS = ["心情", "焦虑", "紧张", "开心", "难过", "委屈", "害怕", "担心", "失眠", "压力"]

DIARY_KEYWORDS = ["日记", "记录一下", "随笔", "今天想记", "宝宝日记", "爸爸日记"]


def classify_intent(text: str) -> IntentClassification:
    normalized = " ".join(text.strip().split())
    if not normalized:
        return general_chat("空消息或无可记录内容。")

    if contains_any(normalized, MEDICAL_TRIAGE_KEYWORDS):
        return IntentClassification("medical_triage", True, True, True, "包含症状或孕期不适线索。")
    if contains_any(normalized, MEDICATION_KEYWORDS):
        return IntentClassification("medication", True, True, True, "包含用药或补充剂相关线索。")
    if contains_any(normalized, REPORT_KEYWORDS):
        triage_required = contains_any(normalized, REPORT_TRIAGE_KEYWORDS)
        reason = "包含检查或报告相关线索。"
        if triage_required:
            reason = "报告描述包含异常、临界或需要复查线索。"
        return IntentClassification("report_review", True, triage_required, True, reason)
    if contains_any(normalized, PREGNANCY_LOG_KEYWORDS):
        return IntentClassification("pregnancy_log", True, False, True, "包含孕期日常记录。")
    if contains_any(normalized, MOOD_KEYWORDS):
        return IntentClassification("mood_support", True, False, True, "包含情绪或陪伴相关内容。")
    if contains_any(normalized, DIARY_KEYWORDS):
        return IntentClassification("diary", True, False, True, "包含日记或回忆记录。")
    return IntentClassification(
        "pregnancy_context",
        True,
        False,
        False,
        "孕妇专属入口默认由宿主 LLM 结合孕期上下文进行语义判断。",
    )


def contains_any(text: str, keywords: list[str]) -> bool:
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def general_chat(reason: str) -> IntentClassification:
    return IntentClassification("general_chat", False, False, False, reason)
