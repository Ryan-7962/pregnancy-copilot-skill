from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

from .adapters.base import MessageAdapter
from .context_package import build_host_context_package
from .data_init import initialize_data_dir
from .event_processor import process_feishu_event
from .intent_router import classify_intent
from .llm import LLMProvider
from .models import MessageEvent
from .profile_readiness import check_profile_readiness
from .profile_onboarding import (
    apply_profile_onboarding_update,
    build_profile_onboarding_event,
    extract_profile_onboarding_update,
    extract_report_observations,
)
from .storage import PregnancyDataStore
from .medical_state import record_medical_observation
from .triage import TriageAdvisor, triage_message


@dataclass
class HostMessageRequest:
    text: str
    sender_id: str
    sender_role: str = "pregnant_user"
    conversation_id: str = "host-conversation"
    channel: str = "host_agent"
    chat_type: str = "p2p"
    timestamp: str | None = None
    message_id: str | None = None
    event_id: str | None = None
    message_type: str = "text"


@dataclass
class HostMessageResult:
    reply_text: str
    event: dict | None
    risk_level: str
    event_id: str
    mode: str
    privacy_level: str
    handled: bool = True
    intent: str = "medical_triage"
    triage_required: bool = True
    artifacts: dict[str, str] = field(default_factory=dict)
    context_package: dict | None = None
    host_action: dict = field(default_factory=dict)


class HostAgentAdapter(MessageAdapter):
    def __init__(self) -> None:
        self.sent_replies: list[tuple[str, str]] = []
        self.docs: dict[str, dict[str, str]] = {}

    def receive_message(self, payload: dict) -> MessageEvent:
        return MessageEvent(
            message_id=payload["message_id"],
            timestamp=payload["timestamp"],
            sender_id=payload["sender_id"],
            sender_role=payload.get("sender_role", "pregnant_user"),
            chat_type=payload.get("chat_type", "p2p"),
            text=payload.get("text", ""),
            source=payload.get("channel", "host_agent"),
            chat_id=payload.get("conversation_id"),
            event_id=payload.get("event_id"),
            message_type=payload.get("message_type", "text"),
        )

    def send_reply(self, message: MessageEvent, text: str) -> None:
        self.sent_replies.append((message.message_id, text))

    def write_doc(self, title: str, content: str) -> str:
        doc_id = f"host-doc-{len(self.docs) + 1:03d}"
        self.docs[doc_id] = {"title": title, "content": content}
        return doc_id


def process_host_message(
    request: HostMessageRequest,
    data_root: str | Path,
    triage_advisor: TriageAdvisor | None = None,
    response_provider: LLMProvider | None = None,
) -> HostMessageResult:
    initialize_data_dir(data_root)
    store = PregnancyDataStore(data_root)
    adapter = HostAgentAdapter()
    payload = build_host_payload(request)
    readiness = check_profile_readiness(data_root)
    intent = classify_intent(request.text)
    pre_triage = triage_message(request.text, advisor=triage_advisor) if intent.triage_required else None
    if readiness["status"] != "ready" and (not pre_triage or pre_triage.risk_level != "red"):
        message = adapter.receive_message(payload)
        raw_path = store.save_raw_message(message)
        onboarding_update = extract_profile_onboarding_update(request.text)
        if onboarding_update.is_profile_intake:
            raw_source_path = raw_path.relative_to(store.root).as_posix()
            apply_profile_onboarding_update(
                store=store,
                update=onboarding_update,
                source_event_id=payload["event_id"],
                raw_source_path=raw_source_path,
            )
            event = build_profile_onboarding_event(
                source_event_id=payload["event_id"],
                timestamp=payload["timestamp"],
                source=request.channel,
                sender_id=request.sender_id,
                chat_id=request.conversation_id,
                raw_source_path=raw_source_path,
                update=onboarding_update,
            )
            store.append_event(event, dedupe_by_event_id=True)
            updated_readiness = check_profile_readiness(data_root)
            reply_text = build_profile_onboarding_saved_reply(updated_readiness, onboarding_update)
            context_package = build_host_context_package(
                store=store,
                user_message=request.text,
                intent="profile_onboarding",
                channel=request.channel,
            )
            return HostMessageResult(
                reply_text=reply_text,
                event=event,
                risk_level="not_applicable",
                event_id=payload["event_id"],
                mode="onboarding",
                privacy_level="summary",
                handled=True,
                intent="profile_onboarding",
                triage_required=False,
                artifacts={"raw_source_path": raw_source_path},
                context_package=context_package,
                host_action=build_host_action(request, handled=True, fallback_reply_text=reply_text),
            )
        reply_text = build_onboarding_reply(readiness)
        context_package = build_host_context_package(
            store=store,
            user_message=request.text,
            intent="profile_onboarding",
            channel=request.channel,
        )
        context_package["system_prompt"] = build_onboarding_system_prompt()
        context_package["context_markdown"] = build_onboarding_context_markdown(readiness)
        context_package["current_medical_state"] = {
            "schema_version": "0.1",
            "metrics": {},
            "open_watch_items": [],
            "resolved_items": [],
            "principle": "Profile is not ready. Do not use template pregnancy age, hospital, nickname, or example medical facts as real facts.",
        }
        context_package["profile_readiness"] = readiness
        context_package["output_contract"] = {
            "reply_mode": "collect_profile_only",
            "must_send_reply_text_as_is": True,
            "do_not_answer_symptom_or_report_yet": True,
            "do_not_assign_green_yellow_red_risk_yet": True,
            "do_not_claim_recorded_as_medical_event": True,
            "ask_for_baseline_profile_and_latest_report": True,
        }
        return HostMessageResult(
            reply_text=reply_text,
            event=None,
            risk_level="profile_needs_review",
            event_id=payload["event_id"],
            mode="onboarding",
            privacy_level="summary",
            handled=True,
            intent="profile_onboarding",
            triage_required=False,
            artifacts={"raw_source_path": raw_path.relative_to(store.root).as_posix()},
            context_package=context_package,
            host_action=build_collect_profile_action(request, reply_text),
        )
    if not intent.handled_by_skill:
        return HostMessageResult(
            reply_text="",
            event=None,
            risk_level="not_applicable",
            event_id="",
            mode="general_chat",
            privacy_level="not_applicable",
            handled=False,
            intent=intent.intent,
            triage_required=False,
            host_action=build_host_action(request, handled=False),
        )
    event = process_feishu_event(
        payload,
        store=store,
        adapter=adapter,
        triage_advisor=triage_advisor,
        response_provider=response_provider,
    )
    report_observations = extract_report_observations(request.text)
    if report_observations:
        for observation in report_observations:
            observation.setdefault("source_event_id", event["event_id"])
            observation.setdefault("raw_source_path", event.get("raw_source_path"))
            record_medical_observation(store, observation)
        event["medical_observations_added"] = [item["metric_key"] for item in report_observations]
        build_current_context_from_store(store)
    reply_text = adapter.sent_replies[-1][1] if adapter.sent_replies else ""
    context_package = build_host_context_package(
        store=store,
        user_message=request.text,
        intent=event["intent"],
        channel=request.channel,
    )
    return HostMessageResult(
        reply_text=reply_text,
        event=event,
        risk_level=event["risk_level"],
        event_id=event["event_id"],
        mode=event["mode"],
        privacy_level=event["privacy_level"],
        handled=True,
        intent=event["intent"],
        triage_required=event["triage_required"],
        artifacts=extract_artifacts(event),
        context_package=context_package,
        host_action=build_host_action(request, handled=True, fallback_reply_text=reply_text),
    )


def build_host_payload(request: HostMessageRequest) -> dict:
    timestamp = request.timestamp or datetime.now(timezone.utc).astimezone().isoformat()
    message_id = request.message_id or f"host-message-{stable_id_seed(request, timestamp)}"
    event_id = request.event_id or f"host-{stable_id_seed(request, timestamp)}"
    return {
        "event_id": event_id,
        "message_id": message_id,
        "timestamp": timestamp,
        "sender_id": request.sender_id,
        "sender_role": request.sender_role,
        "conversation_id": request.conversation_id,
        "channel": request.channel,
        "chat_type": request.chat_type,
        "text": request.text,
        "message_type": request.message_type,
    }


def build_current_context_from_store(store: PregnancyDataStore) -> None:
    from .context_builder import build_current_context

    build_current_context(store)


def stable_id_seed(request: HostMessageRequest, timestamp: str) -> str:
    seed = f"{request.channel}-{request.conversation_id}-{request.sender_id}-{timestamp}"
    return sha256(seed.encode("utf-8")).hexdigest()[:16]


def extract_artifacts(event: dict) -> dict[str, str]:
    artifacts: dict[str, str] = {}
    for key, value in event.items():
        if key.endswith("_path") and isinstance(value, str):
            artifacts[key] = value
    return artifacts


def build_onboarding_reply(readiness: dict) -> str:
    missing = readiness.get("missing_or_template_fields") or []
    missing_text = "、".join(missing) if missing else "基础档案"
    return (
        "先完成孕期建档，再进入正式问答。\n\n"
        "我还不了解你的具体孕期情况。为了让后续回答基于你的真实背景，而不是通用猜测，请先提供目前已有的信息：\n"
        "1. 孕妇基础信息：年龄/出生年、身高、孕前体重、当前体重、所在城市。\n"
        "2. 孕期锚点：末次月经 LMP、预产期 EDD，或当前孕周。\n"
        "3. 就诊信息：医院、下次产检时间、主要医生或科室。\n"
        "4. 最近一次产检/报告：B 超、宫颈长度、胎盘位置、羊水、胎心、血尿常规、甲状腺、糖耐等，有就贴原文或摘要。\n"
        "5. 既往需要长期记住的红黄项：出血/流液史、宫颈问题、胎盘问题、用药、过敏、医生禁忌。\n"
        "6. 偏好：回答语言、语气、是否需要严格医学审计、是否允许同步给家人。\n\n"
        f"当前待补字段：{missing_text}\n\n"
        "隐私说明：这些资料只保存在你指定的本地 pregnancy-data 目录，Skill 不会主动上传或分享；是否经过聊天平台或宿主模型，由你使用的 Agent 和通道决定。\n\n"
        "真实性要求：请按产检报告原文录入数值、单位、日期和医生结论，不要凭印象补全。不知道或没有的数据直接写“未知/未检查/暂未提供”。\n\n"
        "你可以直接发一段“建档信息”，也可以逐次发送报告原文；我会区分报告原文、用户转述和 AI 整理，不会把推断写成医学事实。"
    )


def build_profile_onboarding_saved_reply(readiness: dict, update) -> str:
    updated_fields = "、".join(sorted(update.profile_updates.keys())) or "基础档案"
    observation_count = len(update.observations)
    if readiness["status"] == "ready":
        return (
            "建档信息已保存，当前孕期档案已可用于后续问答。\n\n"
            f"已更新字段：{updated_fields}\n"
            f"已摘录医学指标：{observation_count} 项\n\n"
            "后续同一指标如果有新报告，我会保留旧值作为历史对照，同时把最新同维度数据作为当前判断依据。"
        )
    missing = "、".join(readiness.get("missing_or_template_fields") or [])
    return (
        "建档信息已保存，但档案还没完全就绪。\n\n"
        f"已更新字段：{updated_fields}\n"
        f"已摘录医学指标：{observation_count} 项\n"
        f"仍待补充：{missing}\n\n"
        "你可以继续补充这些字段，补齐后我再进入正式孕期问答。"
    )


def build_onboarding_system_prompt() -> str:
    return (
        "Pregnancy Copilot profile onboarding is required.\n\n"
        "Hard rule: do not answer the user's pregnancy symptom, report, medication, diet, weight, or activity question yet.\n"
        "Hard rule: do not assign green/yellow/red risk yet unless the message contains an immediate emergency red flag.\n"
        "Hard rule: do not say the symptom was recorded as a medical event; only the raw message may have been preserved.\n"
        "Your final response must ask the user to complete the pregnancy profile and provide latest report/checkup data first.\n"
        "Use the provided reply_text exactly when available. Do not add general medical explanation, reassurance, or diagnosis before profile setup.\n"
    )


def build_onboarding_context_markdown(readiness: dict) -> str:
    missing = readiness.get("missing_or_template_fields") or []
    missing_lines = "\n".join(f"- {field}" for field in missing) if missing else "- 基础档案"
    return (
        "# Profile Onboarding Required\n\n"
        "Pregnancy profile is not ready. Do not use template pregnancy age, hospital, nickname, or example medical facts as real facts.\n\n"
        "## Missing Or Template Fields\n\n"
        f"{missing_lines}\n\n"
        "## Required Intake\n\n"
        "- Basic pregnant-user profile.\n"
        "- Pregnancy anchor: LMP, EDD, or current gestational age.\n"
        "- Care context: hospital, city, next checkup when available.\n"
        "- Latest report or checkup data, preserving source and confidence.\n"
        "- Long-term red/yellow watch items, medications, allergies, and doctor orders.\n"
    )


def build_collect_profile_action(request: HostMessageRequest, fallback_reply_text: str) -> dict:
    return {
        "type": "collect_profile",
        "send_reply": True,
        "use_context_package": True,
        "context_package_required": True,
        "target_channel": request.channel,
        "target_conversation_id": request.conversation_id,
        "fallback_reply_text": fallback_reply_text,
        "reason": "Pregnancy profile is not ready; collect baseline pregnancy profile and latest report data before regular answers.",
    }


def build_install_onboarding_action(
    data_root: str | Path,
    channel: str,
    conversation_id: str,
) -> dict:
    """Build the message a host may proactively send immediately after installation."""
    initialize_data_dir(data_root)
    reply_text = build_onboarding_reply(check_profile_readiness(data_root))
    return {
        "type": "collect_profile",
        "send_reply": True,
        "target_channel": channel,
        "target_conversation_id": conversation_id,
        "reply_text": reply_text,
        "reason": "New installation requires a truthful local pregnancy baseline before regular answers.",
    }


def build_host_action(
    request: HostMessageRequest,
    handled: bool,
    fallback_reply_text: str = "",
) -> dict:
    if not handled:
        return {
            "type": "pass_through",
            "send_reply": False,
            "use_context_package": False,
            "target_channel": request.channel,
            "target_conversation_id": request.conversation_id,
            "reason": "Message is outside Pregnancy Copilot scope; host should answer normally.",
        }
    return {
        "type": "answer_with_context_package",
        "send_reply": True,
        "use_context_package": True,
        "context_package_required": True,
        "target_channel": request.channel,
        "target_conversation_id": request.conversation_id,
        "fallback_reply_text": fallback_reply_text,
        "reason": "Pregnancy Copilot handled the message; host should answer using context_package and may use fallback_reply_text if no host LLM is available.",
    }
