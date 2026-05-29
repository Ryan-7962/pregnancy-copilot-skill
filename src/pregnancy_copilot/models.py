from dataclasses import dataclass, field
from typing import Any, Literal

RiskLevel = Literal["green", "yellow", "red"]
PrivacyLevel = Literal["private", "summary", "full"]

@dataclass
class MessageEvent:
    message_id: str
    timestamp: str
    sender_id: str
    sender_role: str
    chat_type: str
    text: str
    source: str = "feishu"
    chat_id: str | None = None
    event_id: str | None = None
    message_type: str | None = None

@dataclass
class TriageResult:
    risk_level: RiskLevel
    reason: str
    red_flags_detected: list[str] = field(default_factory=list)
    missing_questions: list[str] = field(default_factory=list)
    recommended_action: str = ""
    doctor_question_candidates: list[str] = field(default_factory=list)
    must_include_medical_disclaimer: bool = False
    must_recommend_doctor_contact: bool = False
