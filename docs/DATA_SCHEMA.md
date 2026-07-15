# Data Schema: Pregnancy Copilot Skill v0.2.1

The persisted schema version remains `0.1` in this release. v0.2.1 tightens selection, provenance, identity, and write guarantees without rewriting append-only history.

## Principles

1. Preserve source messages and append-only records.
2. Derived files may be rebuilt and atomically replaced.
3. Every medical observation has a date state, source confidence, lifecycle status, and provenance.
4. Undated or low-confidence observations never replace eligible current facts.
5. A data root belongs to one pregnancy identity.

## Directory Layout

```text
pregnancy-data/
├── .locks/                         local process locks
├── inbox/                          idempotent raw message archives
├── events/
│   ├── events.jsonl
│   └── medical_observations.jsonl
├── memory/
│   ├── identity_binding.yaml
│   ├── profile.yaml
│   ├── current_context.md
│   ├── current_medical_state.yaml
│   ├── medical_observation_timeline.md
│   └── daily_metrics.yaml
├── reports/
├── daily_logs/
├── weekly_reviews/
├── baby_diaries/
├── doctor_questions/
└── backups/
```

For a multi-user host, the configured base root additionally contains:

```text
identity_bindings.yaml
identities/<pregnancy_id>/...
```

## Profile

New templates contain no realistic pregnancy facts.

```yaml
schema_version: "0.1"
profile_name: null
display_name: null
baby_nickname: null
last_menstrual_period: null
due_date: null
current_gestational_age: null
gestational_age_as_of: null
timezone: Asia/Shanghai
region: CN
demographics:
  birth_year: null
  age: null
  height_cm: null
  pre_pregnancy_weight_kg: null
  current_weight_kg: null
hospital:
  name: null
  city: null
  care_model: null
next_checkup: null
medical_baseline:
  history: []
  obstetric_history: []
  high_risk_tags: []
  allergies: []
  medications: []
  doctor_orders: []
current_focus: []
```

LMP or EDD is preferred. `current_gestational_age` is only a fallback and should include `gestational_age_as_of` when it must advance over time.

## Message Event

```json
{
  "schema_version": "0.1",
  "event_id": "original-channel-message-id",
  "event_type": "symptom_qa",
  "timestamp": "2026-07-15T10:00:00+08:00",
  "gestational_age": "12w0d",
  "source": "agent_default",
  "sender_role": "pregnant_user",
  "sender_id": "local-channel-user-id",
  "chat_id": "local-conversation-id",
  "raw_source_path": "inbox/raw_agent_default_messages/2026-07-15.md",
  "intent": "medical_triage",
  "triage_required": true,
  "risk_level": "yellow",
  "privacy_level": "summary"
}
```

An ordinary context-only message is preserved in `inbox/` but has no structured event and returns `risk_level: not_applicable`.

## Medical Observation

```json
{
  "schema_version": "0.1",
  "observation_id": "obs-stable-id",
  "metric_key": "cervical_length",
  "display_name": "Cervical length",
  "value": 31,
  "unit": "mm",
  "measured_at": "2026-07-01",
  "recorded_at": "2026-07-15T10:00:00+08:00",
  "status": "confirmed",
  "source_confidence": "user_reported",
  "source_event_id": "original-channel-message-id",
  "raw_source_path": "inbox/raw_agent_default_messages/2026-07-15.md",
  "provenance": {
    "type": "raw_message",
    "reference": "inbox/raw_agent_default_messages/2026-07-15.md",
    "source_event_id": "original-channel-message-id"
  }
}
```

Allowed lifecycle/clinical statuses:

```text
normal | watch | resolved | active | unknown | confirmed | corrected | superseded
```

Source-confidence order:

```text
report_verified > clinician_reported > user_reported > ai_extracted/gemini_inferred > unknown
```

`ai_extracted`, `gemini_inferred`, `unknown`, invalid-date, and explicitly `superseded` observations remain candidates.

## Current Medical State

```yaml
metrics:
  cervical_length:
    display_name: Cervical length
    current:
      value: 31
      unit: mm
      measured_at: 2026-07-01
      source_confidence: user_reported
    previous_values:
      - value: 29
        measured_at: 2026-06-10
        effective_status: superseded
    candidates:
      - value: 30
        measured_at: unknown
        candidate_reason: missing_or_invalid_measured_at
```

Selection order is newest valid date, then source confidence, then `recorded_at`. Candidate records do not compete for current.

## Daily Metrics

`memory/daily_metrics.yaml` is a rebuildable recent index. It keeps dated weight and blood-pressure points plus mood, diet, activity, and sleep summaries. The source event remains authoritative.

```yaml
weight_trend:
  latest:
    value: 53.2
    unit: kg
    date: 2026-07-15
    source_event_id: event-weight
blood_pressure_trend:
  latest:
    systolic: 118
    diastolic: 76
    unit: mmHg
    date: 2026-07-15
    source_event_id: event-bp
days:
  2026-07-15:
    weight: null
    blood_pressure_readings: []
    mood_entries: []
    diet_entries: []
    activity_entries: []
    sleep_entries: []
```

Missing readings remain missing. The index does not infer a clinical interpretation from a numeric change.

## Identity Binding

```yaml
schema_version: "0.1"
identities:
  pregnancy-a:
    data_root: identities/pregnancy-a
    endpoints:
      - channel: agent_default
        conversation_id: pregnancy-a-chat
        sender_id: pregnant-user-a
```

`pregnancy_id` is trusted host configuration. It must not be copied from an untrusted channel payload.

## Write Guarantees

- Raw messages deduplicate on original `message_id` within the daily archive.
- Events deduplicate on `event_id` under a process-safe file lock.
- Medical observations deduplicate on `observation_id`.
- Profile/current-state/context files use atomic replacement.
- Source/channel/path components are validated before filesystem use.
