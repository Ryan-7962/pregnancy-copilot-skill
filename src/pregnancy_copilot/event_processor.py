from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

from .adapters.base import MessageAdapter
from .artifacts import generate_dad_diary, generate_daily_log, week_range_for_timestamp, write_weekly_artifacts
from .context_builder import build_current_context, build_emotional_pattern, build_medical_timeline
from .daily_metrics import build_daily_metrics_index
from .doctor_questions import add_question_candidates, render_doctor_questions_markdown
from .intent_router import IntentClassification, classify_intent
from .llm import LLMProvider
from .models import MessageEvent, TriageResult
from .prompts import PromptBuilder, ResponseWriter
from .router import MessageRoute, route_message
from .storage import PregnancyDataStore, SCHEMA_VERSION
from .triage import TriageAdvisor, triage_message


CN_TZ = timezone(timedelta(hours=8))


def process_feishu_event(
    payload: dict,
    store: PregnancyDataStore,
    adapter: MessageAdapter,
    triage_advisor: TriageAdvisor | None = None,
    response_provider: LLMProvider | None = None,
) -> dict:
    message = adapter.receive_message(payload)
    message.timestamp = normalize_timestamp(message.timestamp)
    raw_path = store.save_raw_message(message)
    route = route_message(message.text, sender_role=message.sender_role, chat_type=message.chat_type)
    intent = classify_intent(route.normalized_text)
    triage = triage_message(route.normalized_text, advisor=triage_advisor) if intent.triage_required else None
    event = build_event_record(message, triage, raw_path.relative_to(store.root).as_posix(), store, route, intent)
    apply_intent_event_type(event, intent)
    if route.mode == "dad_diary":
        event["event_type"] = "dad_diary"
        dad_raw_path = save_dad_diary_raw(store, event["timestamp"], route.normalized_text, message.sender_id)
        diary_path = write_dad_diary(store, event, route.normalized_text)
        event["dad_diary_raw_path"] = dad_raw_path.relative_to(store.root).as_posix()
        event["dad_diary_path"] = diary_path.relative_to(store.root).as_posix()
    elif route.mode == "baby_diary":
        event["event_type"] = "baby_diary"
    elif route.mode == "doctor_questions":
        event["event_type"] = "doctor_question"
        if route.normalized_text and route.normalized_text not in event["doctor_question_candidates"]:
            event["doctor_question_candidates"].insert(0, route.normalized_text)
    store.append_event(event, dedupe_by_event_id=True)
    added_doctor_questions = add_question_candidates(store, event)
    render_doctor_questions_markdown(store)
    weekly_artifacts = None
    if route.mode == "baby_diary":
        start_date, end_date = week_range_for_timestamp(event["timestamp"])
        weekly_artifacts = write_weekly_artifacts(store, start_date, end_date)
    build_current_context(store)
    build_medical_timeline(store)
    build_emotional_pattern(store)
    build_daily_metrics_index(store)
    generate_daily_log(store, event["timestamp"][:10])
    if route.mode == "dad_diary":
        adapter.send_reply(message, "爸爸日记已记录，并已生成整理版。")
    elif route.mode == "baby_diary":
        assert weekly_artifacts is not None
        adapter.send_reply(
            message,
            "宝宝周记已生成。\n"
            f"- 周回顾：{weekly_artifacts['weekly_review_path'].relative_to(store.root).as_posix()}\n"
            f"- 宝宝周记：{weekly_artifacts['baby_diary_path'].relative_to(store.root).as_posix()}",
        )
    elif route.mode == "doctor_questions":
        if added_doctor_questions:
            adapter.send_reply(message, "已加入下次产检待问问题清单。")
        else:
            adapter.send_reply(message, "这条产检问题已在清单中，我没有重复添加。")
    elif not intent.triage_required:
        adapter.send_reply(message, generate_non_triage_reply(intent))
    else:
        adapter.send_reply(
            message,
            generate_response_reply(
                store=store,
                user_message=route.normalized_text,
                triage=triage,
                response_provider=response_provider,
            ),
        )
    return event


def process_event_stream(
    lines: Iterable[str],
    store: PregnancyDataStore,
    adapter: MessageAdapter,
    triage_advisor: TriageAdvisor | None = None,
    response_provider: LLMProvider | None = None,
) -> int:
    processed = 0
    for line in lines:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        process_feishu_event(payload, store, adapter, triage_advisor=triage_advisor, response_provider=response_provider)
        processed += 1
    return processed


def build_event_record(
    message: MessageEvent,
    triage: TriageResult | None,
    raw_source_path: str,
    store: PregnancyDataStore,
    route: MessageRoute | None = None,
    intent: IntentClassification | None = None,
) -> dict:
    profile = store.load_profile()
    timestamp = normalize_timestamp(message.timestamp)
    route = route or route_message(message.text, sender_role=message.sender_role, chat_type=message.chat_type)
    intent = intent or classify_intent(route.normalized_text)
    privacy_level = route.privacy_override or profile.get("privacy", {}).get("default_privacy_level", "summary")
    risk_level = triage.risk_level if triage else "not_applicable"
    risk_reason = triage.reason if triage else intent.reason
    return {
        "schema_version": SCHEMA_VERSION,
        "event_id": message.event_id or message.message_id or f"feishu-{timestamp}",
        "event_type": "symptom_qa",
        "mode": route.mode,
        "command": route.command,
        "timestamp": timestamp,
        "gestational_age": profile.get("current_gestational_age"),
        "source": message.source,
        "sender_role": message.sender_role,
        "sender_id": message.sender_id,
        "chat_id": message.chat_id,
        "chat_type": message.chat_type,
        "raw_source_path": raw_source_path,
        "user_message_summary": summarize_text(route.normalized_text),
        "assistant_response_summary": risk_reason,
        "intent": intent.intent,
        "intent_reason": intent.reason,
        "triage_required": intent.triage_required,
        "risk_level": risk_level,
        "risk_reason": risk_reason,
        "red_flags_detected": triage.red_flags_detected if triage else [],
        "action_items": [triage.recommended_action] if triage and triage.recommended_action else [],
        "doctor_question_candidates": triage.doctor_question_candidates if triage else [],
        "privacy_level": privacy_level,
        "share_status": "not_shared",
    }


def apply_intent_event_type(event: dict, intent: IntentClassification) -> None:
    if intent.intent in {"pregnancy_log", "mood_support", "diary", "medication", "report_review"}:
        event["event_type"] = intent.intent


def generate_non_triage_reply(intent: IntentClassification) -> str:
    if intent.intent == "pregnancy_log":
        return "已记录到孕期日志。"
    if intent.intent == "mood_support":
        return "已记录今天的心情。我也会把这类情绪变化纳入后续陪伴建议里。"
    if intent.intent == "diary":
        return "已记录这段日记素材。"
    if intent.intent == "report_review":
        return "已记录这次报告信息。已摘录的结构化指标会进入当前医学状态；如需医学解读，请补充报告原文、医生结论或异常提示。"
    return "已记录。"


def build_triage_reply(triage: TriageResult) -> str:
    return ResponseWriter().write_triage_reply(triage)


def generate_response_reply(
    store: PregnancyDataStore,
    user_message: str,
    triage: TriageResult,
    response_provider: LLMProvider | None = None,
) -> str:
    fallback = ResponseWriter().write_triage_reply(triage)
    if not response_provider:
        return fallback
    context_path = store.root / "memory" / "current_context.md"
    context = context_path.read_text(encoding="utf-8") if context_path.exists() else ""
    prompt = PromptBuilder().build_pregnancy_qa_prompt(
        context=context,
        user_message=user_message,
        risk_level=triage.risk_level,
    )
    response = response_provider.generate(prompt).strip()
    if not response:
        return fallback
    if triage.risk_level == "red" and "尽快联系产科医生" not in response:
        response = response.rstrip() + "\n\n这类情况不建议继续只问 AI，请尽快联系产科医生、产科急诊或医院急诊。"
    return response


def summarize_text(text: str, limit: int = 80) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1] + "…"


def normalize_timestamp(value: str) -> str:
    if value and value.isdigit():
        number = int(value)
        if number > 10_000_000_000:
            number = number / 1000
        return datetime.fromtimestamp(number, tz=CN_TZ).isoformat()
    if value:
        return value
    return datetime.now(tz=CN_TZ).isoformat()


def save_dad_diary_raw(store: PregnancyDataStore, timestamp: str, text: str, sender_id: str) -> Path:
    store.ensure_dirs()
    path = store.root / "inbox" / "raw_dad_diary" / f"{timestamp[:10]}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n\n---\n")
        handle.write(f"timestamp: {timestamp}\n")
        handle.write(f"sender_id: {sender_id}\n")
        handle.write("source: feishu\n")
        handle.write("---\n\n")
        handle.write(text.strip() + "\n")
    return path


def write_dad_diary(store: PregnancyDataStore, event: dict, text: str) -> Path:
    profile = store.load_profile()
    diary = generate_dad_diary(
        raw_text=text,
        gestational_age=event.get("gestational_age") or profile.get("current_gestational_age", "unknown"),
        mood="待补充",
        baby_status="继续成长",
    )
    path = store.root / "baby_diaries" / f"dad-diary-{event['timestamp'][:10]}-{event['event_id']}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(diary + "\n", encoding="utf-8")
    return path
