from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
import re
from typing import Any

from .context_builder import read_events
from .context_builder import format_gestational_age
from .storage import PregnancyDataStore


MEDICAL_PROMISES = ["我很健康", "一切正常", "妈妈不用担心"]


def _strip_private_lines(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if "[private]" not in line and "privacy: private" not in line)


def generate_husband_summary(daily_log: str, privacy_level: str = "summary") -> str:
    visible_log = _strip_private_lines(daily_log)
    if privacy_level == "private":
        visible_log = "今天有内容被标记为 private，不同步细节。"

    return "\n".join(
        [
            "# 老公 Summary 日报",
            "",
            "## 今日身体状态",
            _extract_section_hint(visible_log, "身体") or "请查看今日日志摘要，重点关注是否有不适变化。",
            "",
            "## 今日情绪状态",
            _extract_section_hint(visible_log, "情绪") or "今天的情绪需要温柔、稳定的陪伴。",
            "",
            "## 今日她最需要的支持",
            "少讲道理，多陪伴；帮她把问题记录下来，必要时一起问医生。",
            "",
            "## 伴侣可以做的 3 件事",
            "- 主动问她现在最需要你做什么。",
            "- 帮她准备水、休息环境和产检资料。",
            "- 晚上一起复盘需要记录或询问医生的问题。",
            "",
            "## 明日提醒",
            "继续观察身体变化；如出现红旗症状，优先联系医生或就医。",
        ]
    )


def generate_daily_log(store: PregnancyDataStore, date: str) -> Path:
    store.ensure_dirs()
    events = [event for event in read_events(store) if str(event.get("timestamp", "")).startswith(date)]
    lines = [
        f"# Daily Log {date}",
        "",
        "> Generated from append-only events.jsonl. Private event details are intentionally hidden.",
        "",
        "## 今日身体状态",
        "",
    ]
    visible_events = [event for event in events if event.get("privacy_level") != "private"]
    private_events = [event for event in events if event.get("privacy_level") == "private"]

    if visible_events:
        for event in visible_events:
            lines.append(format_daily_event(event))
    else:
        lines.append("- 暂无可同步事件。")

    lines.extend(["", "## 隐私占位", ""])
    if private_events:
        lines.extend(f"- [private] {event.get('event_id', 'unknown')}" for event in private_events)
    else:
        lines.append("- 暂无。")

    lines.extend(["", "## 今日风险记录", ""])
    risk_counts = count_risks(events)
    if risk_counts:
        for risk in ["red", "yellow", "green"]:
            if risk_counts.get(risk):
                lines.append(f"- {risk}: {risk_counts[risk]}")
    else:
        lines.append("- 暂无。")

    lines.extend(["", "## 下次产检待问问题", ""])
    questions = collect_doctor_questions(events)
    if questions:
        lines.extend(f"- {question}" for question in questions)
    else:
        lines.append("- 暂无。")

    lines.extend(["", "## 明日提醒", "", "- 继续记录症状变化、饮食、情绪、用药和产检问题。"])
    path = store.root / "daily_logs" / f"{date}.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def generate_dad_diary(raw_text: str, gestational_age: str, mood: str, baby_status: str) -> str:
    safe_status = _sanitize_baby_status(baby_status)
    title = f"{format_gestational_age(gestational_age)}｜心情：{mood}｜宝宝状态：{safe_status}"
    return "\n".join(
        [
            f"# {title}",
            "",
            "## 爸爸原文",
            raw_text.strip(),
            "",
            "## AI 整理版",
            raw_text.strip(),
            "",
            "## 今日照片",
            "",
            "## 可选宝宝视角",
            "爸爸妈妈今天都在认真记录，也会把不确定的问题准备好问医生。",
        ]
    )


def format_daily_event(event: dict[str, Any]) -> str:
    summary = event.get("user_message_summary") or event.get("event_id", "未命名事件")
    risk = event.get("risk_level", "unknown")
    action_items = event.get("action_items") or []
    if event.get("triage_required") is False or risk == "not_applicable":
        line = f"- {summary}"
    else:
        line = f"- [{risk}] {summary}"
    if action_items:
        line += f"；行动：{'；'.join(str(item) for item in action_items)}"
    return line


def count_risks(events: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        if event.get("triage_required") is False:
            continue
        risk = event.get("risk_level")
        if risk in {"green", "yellow", "red"}:
            counts[str(risk)] = counts.get(str(risk), 0) + 1
    return counts


def collect_doctor_questions(events: list[dict[str, Any]]) -> list[str]:
    questions = []
    seen = set()
    for event in events:
        for question in event.get("doctor_question_candidates") or []:
            if question not in seen:
                seen.add(question)
                questions.append(question)
    return questions


def generate_baby_weekly_diary(
    gestational_week: str,
    weekly_review: str,
    dad_diaries: str,
    prenatal_events: str,
    baby_nickname: str = "宝宝",
) -> str:
    diary = "\n".join(
        [
            f"# {gestational_week} {baby_nickname}周记",
            "",
            f"我是{baby_nickname}，这一周我听见爸爸妈妈在认真生活，也在认真记录我的成长。",
            "",
            "## 这一周",
            weekly_review.strip(),
            "",
            "## 爸爸的记录",
            dad_diaries.strip(),
            "",
            "## 产检小记",
            _safe_prenatal_sentence(prenatal_events),
        ]
    )
    for phrase in MEDICAL_PROMISES:
        diary = diary.replace(phrase, "爸爸妈妈认真记录，准备问医生")
    return diary


def generate_weekly_review(store: PregnancyDataStore, start_date: str, end_date: str) -> str:
    events = events_in_date_range(read_events(store), start_date, end_date)
    visible_events = [event for event in events if event.get("privacy_level") != "private"]
    private_events = [event for event in events if event.get("privacy_level") == "private"]
    lines = [
        f"# Weekly Review {start_date} to {end_date}",
        "",
        "> Generated from append-only events.jsonl. Private event details are intentionally hidden.",
        "",
        "## 本周身体与问题记录",
        "",
    ]
    if visible_events:
        lines.extend(format_daily_event(event) for event in visible_events)
    else:
        lines.append("- 暂无可同步事件。")

    lines.extend(["", "## 隐私占位", ""])
    if private_events:
        lines.extend(f"- [private] {event.get('event_id', 'unknown')}" for event in private_events)
    else:
        lines.append("- 暂无。")

    lines.extend(["", "## 本周风险分布", ""])
    risk_counts = count_risks(events)
    if risk_counts:
        for risk in ["red", "yellow", "green"]:
            if risk_counts.get(risk):
                lines.append(f"- {risk}: {risk_counts[risk]}")
    else:
        lines.append("- 暂无。")

    lines.extend(["", "## 下次产检待问问题", ""])
    questions = collect_doctor_questions(events)
    if questions:
        lines.extend(f"- {question}" for question in questions)
    else:
        lines.append("- 暂无。")

    lines.extend(["", "## 爸爸记录", ""])
    dad_events = [event for event in visible_events if event.get("event_type") == "dad_diary"]
    if dad_events:
        lines.extend(f"- {event.get('user_message_summary', event.get('event_id', ''))}" for event in dad_events)
    else:
        lines.append("- 暂无。")

    lines.extend(["", "## 下周关注", "", "- 继续记录症状、产检问题、情绪变化和伴侣可支持事项。"])
    return "\n".join(lines) + "\n"


def write_weekly_artifacts(store: PregnancyDataStore, start_date: str, end_date: str) -> dict[str, Path]:
    store.ensure_dirs()
    review = generate_weekly_review(store, start_date, end_date)
    slug = f"{start_date}_to_{end_date}"
    weekly_review_path = store.root / "weekly_reviews" / f"{slug}.md"
    weekly_review_path.write_text(review, encoding="utf-8")

    events = events_in_date_range(read_events(store), start_date, end_date)
    visible_events = [event for event in events if event.get("privacy_level") != "private"]
    profile = store.load_profile()
    baby_diary = generate_baby_weekly_diary(
        gestational_week=weekly_gestational_label(profile, visible_events),
        weekly_review=review,
        dad_diaries="\n".join(
            event.get("user_message_summary", "")
            for event in visible_events
            if event.get("event_type") == "dad_diary"
        )
        or "爸爸妈妈这一周都在认真记录。",
        prenatal_events="\n".join(
            event.get("user_message_summary", "")
            for event in visible_events
            if event.get("event_type") in {"prenatal_report", "report_question", "medication_question"}
            or event.get("risk_level") in {"yellow", "red"}
        ),
        baby_nickname=profile.get("baby_nickname") or "宝宝",
    )
    baby_diary_path = store.root / "baby_diaries" / f"week-{slug}.md"
    baby_diary_path.write_text(baby_diary + "\n", encoding="utf-8")
    return {"weekly_review_path": weekly_review_path, "baby_diary_path": baby_diary_path}


def week_range_for_timestamp(timestamp: str) -> tuple[str, str]:
    current = datetime.fromisoformat(timestamp).date()
    start = current - timedelta(days=current.weekday())
    end = start + timedelta(days=6)
    return start.isoformat(), end.isoformat()


def events_in_date_range(events: list[dict[str, Any]], start_date: str, end_date: str) -> list[dict[str, Any]]:
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    result = []
    for event in events:
        timestamp = str(event.get("timestamp", ""))
        if len(timestamp) < 10:
            continue
        event_date = date.fromisoformat(timestamp[:10])
        if start <= event_date <= end:
            result.append(event)
    return result


def weekly_gestational_label(profile: dict[str, Any], events: list[dict[str, Any]]) -> str:
    for event in reversed(events):
        value = event.get("gestational_age")
        if value:
            return format_gestational_age(value).split("+", maxsplit=1)[0]
    value = profile.get("current_gestational_age")
    if value:
        return format_gestational_age(value).split("+", maxsplit=1)[0]
    return "W?"


def _extract_section_hint(text: str, keyword: str) -> str:
    for line in text.splitlines():
        if keyword in line and not line.startswith("##"):
            return line.strip("- ").strip()
    return ""


def _sanitize_baby_status(status: str) -> str:
    if any(word in status for word in ["健康", "正常", "没事"]):
        return "继续成长"
    return status


def _safe_prenatal_sentence(prenatal_events: str) -> str:
    if re.search(r"报告|医生|产检|复查|异常|问题", prenatal_events):
        return "有些产检和报告内容，爸爸妈妈认真记录，准备问医生。"
    return "爸爸妈妈把这一周的重要事情记录了下来。"
