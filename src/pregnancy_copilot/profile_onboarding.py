from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .context_builder import build_current_context
from .medical_state import record_medical_observation
from .storage import PregnancyDataStore, SCHEMA_VERSION, atomic_write_text


@dataclass
class ProfileOnboardingUpdate:
    is_profile_intake: bool = False
    profile_updates: dict[str, Any] = field(default_factory=dict)
    observations: list[dict[str, Any]] = field(default_factory=list)


def extract_profile_onboarding_update(text: str, as_of: str | None = None) -> ProfileOnboardingUpdate:
    normalized = normalize_text(text)
    has_profile_marker = any(marker in normalized for marker in ["建档", "基础信息", "孕期锚点", "预产期", "LMP"])
    has_pregnancy_anchor = bool(re.search(r"\b\d{1,2}w[+\d]*d?\b|孕\s*\d{1,2}\s*[周w]", normalized, re.I))
    has_report_marker = any(marker in normalized for marker in ["NT", "CRL", "胎心", "B超", "产检", "报告"])
    has_structured_field = any(
        marker in normalized
        for marker in ["称呼", "出生", "年龄", "身高", "孕前体重", "当前体重", "所在城市", "产检医院", "既往史", "孕产史", "过敏", "医嘱", "下次产检"]
    )
    has_dated_anchor = bool(re.search(r"(?:LMP|EDD|预产期)[:：]?\s*\d{4}[-/.]\d{1,2}[-/.]\d{1,2}", normalized, re.I))
    if not ((has_profile_marker and (has_pregnancy_anchor or has_report_marker or has_dated_anchor)) or has_structured_field):
        return ProfileOnboardingUpdate()

    updates: dict[str, Any] = {
        "timezone": "Asia/Shanghai",
        "region": "CN",
    }
    display_name = match_first(normalized, [r"孕妇基础信息[:：]\s*([^，,\n]+)", r"称呼[:：]\s*([^，,\n]+)"])
    if display_name:
        updates["display_name"] = display_name.strip()
        updates["profile_name"] = f"{display_name.strip()} Pregnancy Profile"

    demographics: dict[str, Any] = {}
    birth_year = match_first(normalized, [r"(\d{4})\s*年出生"])
    age = match_first(normalized, [r"(?:年龄[:：]?\s*)?(\d{2})\s*岁"])
    height = match_first(normalized, [r"身高[:：]?\s*([0-9]+(?:\.[0-9]+)?)\s*cm"])
    pre_weight = match_first(normalized, [r"孕前体重[:：]?\s*([0-9]+(?:\.[0-9]+)?)\s*kg"])
    current_weight = match_first(normalized, [r"当前体重[:：]?\s*([0-9]+(?:\.[0-9]+)?)\s*kg"])
    if birth_year:
        demographics["birth_year"] = int(birth_year)
    if age:
        demographics["age"] = int(age)
    if height:
        demographics["height_cm"] = float(height)
    if pre_weight:
        demographics["pre_pregnancy_weight_kg"] = float(pre_weight)
    if current_weight:
        demographics["current_weight_kg"] = float(current_weight)
    if demographics:
        updates["demographics"] = demographics
    baby_nickname = match_first(normalized, [r"(?:宝宝昵称|胎儿昵称|宝宝叫|胎儿叫)[:：]?\s*([^，,；;\n]+)"])
    if baby_nickname:
        updates["baby_nickname"] = baby_nickname.strip()
    elif "虚拟测试" in normalized or "测试孕妇" in normalized:
        updates["baby_nickname"] = "测试宝宝"

    gestational_age = match_first(normalized, [r"(?:当前孕周|孕周)[:：]?\s*(\d{1,2}\s*w\s*\+?\s*\d?\s*d?)", r"孕\s*(\d{1,2})\s*周\s*\+?\s*(\d?)\s*天?"])
    if gestational_age:
        updates["current_gestational_age"] = normalize_gestational_age(gestational_age)
        updates["gestational_age_as_of"] = as_of[:10] if as_of else None
    lmp = match_first(normalized, [r"LMP[:：]?\s*(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})", r"末次月经[:：]?\s*(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})"])
    if lmp:
        updates["last_menstrual_period"] = normalize_date(lmp)
    due_date = match_first(normalized, [r"(?:EDD|预产期)[:：]?\s*(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})"])
    if due_date:
        updates["due_date"] = normalize_date(due_date)

    city = match_first(normalized, [r"所在城市[:：]?\s*([^，,。；;\n]+)", r"城市[:：]?\s*([^，,。；;\n]+)"])
    hospital_name = match_first(normalized, [r"就诊信息[:：]\s*([^，,。；;\n]+)", r"(?:产检医院|医院)[:：]?\s*([^，,。；;\n]+)"])
    hospital: dict[str, Any] = {}
    if hospital_name:
        hospital["name"] = hospital_name.strip()
    if city:
        hospital["city"] = city.strip()
    if hospital:
        updates["hospital"] = hospital

    next_checkup = match_first(normalized, [r"(?:下次产检|下次检查)(?:约|[:：])?\s*(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})"])
    if next_checkup:
        updates["next_checkup"] = normalize_date(next_checkup)

    medications = []
    medication = match_first(normalized, [r"(?:目前服用|用药)[:：]?\s*([^。；;\n]+)"])
    if medication:
        medications.append(medication.strip())
    allergies = []
    if "无已知药物过敏" in normalized:
        allergies.append("无已知药物过敏")
    elif allergy := match_first(normalized, [r"过敏[:：]\s*([^，,。；;\n]+)"]):
        allergies.append(allergy.strip())
    baseline = {}
    if medications or allergies:
        baseline["medications"] = medications
        baseline["allergies"] = allergies
    history = match_first(normalized, [r"既往史[:：]\s*([^，,。；;\n]+)"])
    obstetric_history = match_first(normalized, [r"孕产史[:：]\s*([^，,。；;\n]+)"])
    doctor_order = match_first(normalized, [r"(?:医生医嘱|医嘱)[:：]\s*([^，,。；;\n]+)"])
    if history:
        baseline["history"] = [history]
    if obstetric_history:
        baseline["obstetric_history"] = [obstetric_history]
    if doctor_order:
        baseline["doctor_orders"] = [doctor_order]
    if baseline:
        updates["medical_baseline"] = baseline

    current_focus = match_first(normalized, [r"(?:当前关注|关注事项)[:：]\s*([^，,。；;\n]+)"])
    if current_focus:
        updates["current_focus"] = [current_focus]

    preferences = {}
    if "简体中文" in normalized:
        preferences["language"] = "zh-CN"
    if "清晰克制" in normalized or "清晰、克制" in normalized:
        preferences["tone"] = "清晰、克制、结构化"
    if "默认不向家人同步" in normalized or "不向家人同步" in normalized:
        preferences["partner_share_default"] = "private"
        preferences["husband_share_default"] = "private"
    if preferences:
        updates["preferences"] = preferences

    measured_at = match_first(normalized, [r"(?:最近一次产检/报告|最近一次产检|报告)[:：]?\s*(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})"])
    measured_at = normalize_date(measured_at) if measured_at else ""
    observations = extract_initial_observations(normalized, measured_at=measured_at)
    return ProfileOnboardingUpdate(is_profile_intake=True, profile_updates=updates, observations=observations)


def apply_profile_onboarding_update(
    store: PregnancyDataStore,
    update: ProfileOnboardingUpdate,
    source_event_id: str,
    raw_source_path: str,
) -> dict[str, Any]:
    profile_path = store.root / "memory" / "profile.yaml"
    with store.transaction_lock("profile"):
        profile = store.load_profile()
        deep_merge(profile, update.profile_updates)
        atomic_write_text(profile_path, yaml.safe_dump(profile, allow_unicode=True, sort_keys=False))

    for observation in update.observations:
        observation.setdefault("source_event_id", source_event_id)
        observation.setdefault("raw_source_path", raw_source_path)
        record_medical_observation(store, observation)
    build_current_context(store)
    return profile


def build_profile_onboarding_event(
    source_event_id: str,
    timestamp: str,
    source: str,
    sender_id: str,
    chat_id: str,
    raw_source_path: str,
    update: ProfileOnboardingUpdate,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "event_id": source_event_id,
        "event_type": "profile_onboarding",
        "mode": "onboarding",
        "timestamp": timestamp,
        "source": source,
        "sender_role": "pregnant_user",
        "sender_id": sender_id,
        "chat_id": chat_id,
        "raw_source_path": raw_source_path,
        "user_message_summary": "建档信息",
        "assistant_response_summary": "已保存建档信息",
        "intent": "profile_onboarding",
        "triage_required": False,
        "risk_level": "not_applicable",
        "risk_reason": "Profile onboarding intake",
        "profile_fields_updated": sorted(update.profile_updates.keys()),
        "medical_observations_added": [item["metric_key"] for item in update.observations],
        "privacy_level": "summary",
        "share_status": "not_shared",
    }


def extract_initial_observations(text: str, measured_at: str) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    measured_at = measured_at or "unknown"
    for metric_key, display_name, pattern, unit in [
        ("nt", "NT", r"NT\s*([0-9]+(?:\.[0-9]+)?)\s*mm", "mm"),
        ("crl", "CRL", r"CRL\s*([0-9]+(?:\.[0-9]+)?)\s*mm", "mm"),
        ("fetal_heart_rate", "胎心", r"胎心\s*([0-9]+)\s*bpm", "bpm"),
    ]:
        value = match_first(text, [pattern])
        if value:
            observations.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "metric_key": metric_key,
                    "display_name": display_name,
                    "value": value,
                    "unit": unit,
                    "measured_at": measured_at,
                    "status": "unknown",
                    "source_confidence": "user_reported",
                    "interpretation": "建档信息数值摘录；未自动判断正常或异常，待按报告/医生原结论确认。",
                }
            )
    placenta = match_first(text, [r"胎盘\s*([^，,；;\n]+)"])
    if placenta:
        observations.append(
            {
                "schema_version": SCHEMA_VERSION,
                "metric_key": "placenta_position",
                "display_name": "胎盘位置",
                "value": placenta.strip(),
                "measured_at": measured_at,
                "status": "unknown",
                "source_confidence": "user_reported",
                "interpretation": "建档信息原文摘录；未自动判断正常或异常，待按报告/医生原结论确认。",
            }
        )
    return observations


def extract_report_observations(text: str) -> list[dict[str, Any]]:
    normalized = normalize_text(text)
    has_report_marker = any(marker in normalized for marker in ["新报告", "产检报告", "B超", "NT", "CRL", "胎心"])
    if not has_report_marker:
        return []
    measured_at = match_first(normalized, [r"(?:新报告|产检报告|报告|B超)[:：]?\s*(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})"])
    measured_at = normalize_date(measured_at) if measured_at else "unknown"
    observations = extract_initial_observations(normalized, measured_at=measured_at or "unknown")
    for observation in observations:
        observation["interpretation"] = "产检报告消息数值摘录；未自动判断正常或异常，待按报告/医生原结论确认。"
    return observations


def normalize_text(text: str) -> str:
    return text.replace("＋", "+").replace("Ｗ", "W").replace("ｗ", "w")


def match_first(text: str, patterns: list[str]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if not match:
            continue
        if len(match.groups()) >= 2 and match.group(2):
            return f"{match.group(1)}w{match.group(2)}d"
        return clean_value(match.group(1))
    return None


def clean_value(value: str) -> str:
    return value.strip().strip("。.;； ")


def normalize_gestational_age(value: str) -> str:
    compact = re.sub(r"\s+", "", value.lower()).replace("+", "")
    if re.fullmatch(r"\d{1,2}w\d?d?", compact):
        if compact.endswith("w"):
            return compact + "0d"
        if compact.endswith("d"):
            return compact
        return compact + "d"
    return compact


def normalize_date(value: str | None) -> str | None:
    if not value:
        return None
    parts = re.split(r"[-/.]", value)
    if len(parts) != 3:
        return value
    year, month, day = parts
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def deep_merge(target: dict[str, Any], updates: dict[str, Any]) -> None:
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            deep_merge(target[key], value)
        else:
            target[key] = value
