# Data Schema：Pregnancy Copilot Skill v0.1

## 1. 数据设计原则

1. 原文完整保存，不直接丢弃。
2. 日常回答只读取压缩后的上下文，不全量读取原文。
3. 事件流 append-only，不覆盖旧事件。
4. 每条事件带 `schema_version`。
5. 医学事实必须可追溯到 source。
6. 数据与代码分离，便于升级和迁移。

## 2. 目录结构

```text
pregnancy-data/
├── inbox/
│   ├── raw_feishu_messages/
│   ├── raw_gemini_exports/
│   ├── raw_notebooklm_exports/
│   ├── raw_obsidian_notes/
│   └── raw_dad_diary/
├── events/
│   ├── events.jsonl
│   ├── medical_events.jsonl
│   ├── emotion_events.jsonl
│   └── diary_events.jsonl
├── memory/
│   ├── profile.yaml
│   ├── current_context.md
│   ├── long_term_summary.md
│   ├── medical_timeline.md
│   ├── current_medical_state.yaml
│   ├── medical_observation_timeline.md
│   ├── emotional_pattern.md
│   └── preferences.yaml
├── reports/
├── daily_logs/
├── weekly_reviews/
├── husband_summaries/
├── baby_diaries/
├── doctor_questions/
│   ├── questions.jsonl
│   └── questions.md
├── feishu_docs/
├── exports/
└── backups/
```

## 3. profile.yaml

```yaml
schema_version: "0.1"
profile_name: "User Pregnancy Profile"
display_name: "孕妇"
baby_nickname: "宝宝"
due_date: null
current_gestational_age: null
timezone: "Asia/Shanghai"
region: "CN"
hospital:
  name: null
  city: null
  care_model: "中国大陆主要妇产科医院流程"
preferences:
  language: "zh-CN"
  tone: "温柔、清晰、克制"
  medical_disclaimer_level: "risk_based"
  partner_share_default: "private"
  husband_share_default: "private"
privacy:
  default_privacy_level: "summary"
  require_confirmation_for_full_share: true
medical_baseline:
  high_risk_tags: []
  allergies: []
  medications: []
  doctor_orders: []
```

## 4. events.jsonl 基础事件

每行一个 JSON 对象。

```json
{
  "schema_version": "0.1",
  "event_id": "2026-05-01T21-30-00-feishu-001",
  "event_type": "symptom_qa",
  "timestamp": "2026-05-01T21:30:00+08:00",
  "gestational_age": "20w0d",
  "source": "feishu",
  "sender_role": "pregnant_user",
  "raw_source_path": "inbox/raw_feishu_messages/2026-05-01.md",
  "user_message_summary": "询问肚皮发紧是否正常",
  "assistant_response_summary": "偶发肚皮发紧，休息后缓解，暂无红旗症状，建议记录频率。",
  "risk_level": "green",
  "risk_reason": "无出血、流水、持续腹痛等红旗症状",
  "symptoms": ["肚皮发紧"],
  "red_flags_detected": [],
  "red_flags_denied": ["出血", "流水", "持续腹痛"],
  "action_items": ["记录频率", "休息后观察是否缓解"],
  "doctor_question_candidates": ["肚皮发紧是否需要关注宫颈长度？"],
  "privacy_level": "summary",
  "share_status": "not_shared"
}
```

## 5. medical_events.jsonl

```json
{
  "schema_version": "0.1",
  "event_id": "2026-03-26-ultrasound-16w",
  "event_type": "prenatal_report",
  "timestamp": "2026-03-26T10:00:00+08:00",
  "gestational_age": "15w6d",
  "source": "obsidian_import",
  "raw_source_path": "reports/2026-03-26-ultrasound-16w.md",
  "facts": [
    {
      "item": "胎心",
      "value": "155",
      "unit": "次/分",
      "interpretation": null,
      "source_quote": "胎心强劲 155 次/分"
    }
  ],
  "doctor_conclusion": [],
  "ai_summary": "本次报告显示若干此前关注点得到改善或解除。具体医学判断以医生结论为准。",
  "privacy_level": "summary"
}
```

## 6. diary_events.jsonl

```json
{
  "schema_version": "0.1",
  "event_id": "2026-05-01-dad-diary",
  "event_type": "dad_diary",
  "timestamp": "2026-05-01T22:00:00+08:00",
  "gestational_age": "20w0d",
  "source": "feishu",
  "raw_source_path": "inbox/raw_dad_diary/2026-05-01.md",
  "title": "W20+0｜心情：紧张转安心｜宝宝状态：稳定成长",
  "summary": "爸爸记录了产检前后的陪伴和情绪变化。",
  "artifacts": [
    "feishu_docs/dad_diary_2026-05-01.md"
  ],
  "privacy_level": "private"
}
```

## 6.1 medical_observations.jsonl

`events/medical_observations.jsonl` 保存从 B 超、化验、医生医嘱或人工录入中提取的结构化医学指标。它是 append-only 的：新检查不会删除旧值，而是通过 `memory/current_medical_state.yaml` 刷新“当前有效状态”。

```json
{
  "schema_version": "0.1",
  "observation_id": "obs-placenta-0508",
  "metric_key": "placenta_position",
  "display_name": "胎盘位置",
  "value": "宫底后壁",
  "measured_at": "2026-05-08",
  "status": "resolved",
  "interpretation": "旧 23mm 状态已被刷新，当前胎盘低置警报解除。",
  "source_event_id": "evt-0508-us",
  "raw_source_path": "reports/2026-05-08-ultrasound.md"
}
```

`status`：

```text
normal：当前正常
watch：当前仍需随访/复查
resolved：旧风险或旧异常已被新检查刷新
active：当前仍有效的医嘱、用药或限制
unknown：已记录但状态未定，需要人工确认
```

`memory/current_medical_state.yaml` 按 `metric_key` 聚合并只把最新检查作为 `current`。旧值进入 `previous_values`，并标记为 `effective_status: superseded`，避免大模型继续把过期数据当作当前状态。

## 7. privacy_level

```text
private：敏感记录，不进入可共享摘要
summary：进入孕妇本地摘要；如开启协作者共享，只同步过滤后的摘要和关心建议
full：完整共享请求，需要孕妇确认
```

## 8. risk_level

```text
green：可观察，记录即可
yellow：建议联系医生/产检重点咨询
red：建议立即联系产科医生/产科急诊/急诊/120
not_applicable：非医学分级事件，例如体重、饮食、心情、日记；不应展示红黄绿或纳入风险统计
```

## 9. doctor_questions/questions.jsonl

产检问题清单是可更新的工作清单，不属于主事件流。主事件仍保留在 `events/events.jsonl`，问题状态可以随产检进展更新。

```json
{
  "schema_version": "0.1",
  "question_id": "dq-evt-report-1-12345",
  "question": "B 超报告是否需要复查？",
  "status": "open",
  "created_at": "2026-05-05T09:00:00+08:00",
  "updated_at": "2026-05-05T09:00:00+08:00",
  "source_event_id": "evt-report",
  "source": "feishu",
  "raw_source_path": "inbox/raw_feishu_messages/2026-05-05.md",
  "gestational_age": "20w0d",
  "risk_level": "yellow",
  "answer_summary": null
}
```

状态：

```text
open：待问
asked：已带到产检/已询问，等待结论沉淀
answered：已有医生结论摘要
archived：不再追踪
```

## 10. 原文与摘要的关系

- `inbox/` 保存原始消息。
- `events/` 保存结构化事件和 raw_source_path。
- `memory/` 保存压缩上下文。
- v2 可从 events 重放生成新的 summary。
