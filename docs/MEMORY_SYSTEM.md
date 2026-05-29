# Memory System

Pregnancy Copilot v0.1 uses a local, auditable file memory system. It does not require a cloud database or vector database.

## Core Idea

The system separates memory into six layers:

1. Raw memory
2. Event memory
3. Medical state memory
4. Source confidence and review memory
5. Working context
6. Generated artifacts

This keeps original data safe while allowing summaries and prompts to be regenerated as the product improves.

## 1. Raw Memory

Raw user input is preserved under `pregnancy-data/inbox/`.

Examples:

```text
inbox/raw_feishu_messages/YYYY-MM-DD.md
inbox/raw_dad_diary/YYYY-MM-DD.md
inbox/raw_gemini_exports/
inbox/raw_notebooklm_exports/
inbox/raw_obsidian_notes/
```

Raw memory is for traceability. The assistant should not read all raw memory for every answer.

## 2. Event Memory

Structured events are appended to JSONL files under `pregnancy-data/events/`.

Main file:

```text
events/events.jsonl
```

Each event includes:

- `schema_version`
- `event_id`
- `event_type`
- `timestamp`
- `gestational_age`
- `source`
- `raw_source_path`
- `user_message_summary`
- `assistant_response_summary`
- `risk_level`
- `doctor_question_candidates`
- `privacy_level`

Events are append-only. Corrections should be new events, not edits to old events.

Medical observations use a dedicated append-only file:

```text
events/medical_observations.jsonl
```

This file stores structured measurements such as placenta position, cervical length, thyroid labs, urine findings, fetal biometry, and doctor restrictions.

## 3. Medical State Memory

Not every old medical value should remain current. Pregnancy measurements are time-sensitive, and later reports can resolve, supersede, or reactivate earlier risks.

The current effective medical state is regenerated into:

```text
memory/current_medical_state.yaml
memory/medical_observation_timeline.md
```

Rules:

- Preserve every original observation in `events/medical_observations.jsonl`.
- Group observations by `metric_key`.
- Use the latest `measured_at` value as `current`.
- If the same metric has the same `measured_at`, use the later `recorded_at` value as `current`.
- Move older values to `previous_values` with `effective_status: superseded`.
- Give host LLMs `current` first, then history, so stale report data does not drive current medical reasoning.
- Reject structured medical observations that lack `measured_at`; the host should ask the user for the report date instead of guessing.
- If the current memory has no reliable fact for a question, the host should say it does not know or ask for the missing report text, date, value, unit, or doctor conclusion.

## 3.1 Daily Metrics Memory

High-frequency daily data such as weight, mood, diet, activity, and sleep is not stored as a medical observation by default. It is extracted from official non-private events into:

```text
memory/daily_metrics.yaml
memory/daily_metrics.md
```

Rules:

- Preserve the original daily record in `events/events.jsonl` and the generated daily log.
- Extract quick-read summaries from `user_message_summary`, not from private raw text.
- Weight entries are tracked as points with `value`, `unit`, `date`, and `source_event_id`.
- The index exposes `latest`, `previous`, and `delta_kg` for simple trend comparison.
- Mood, diet, activity, and sleep are kept as dated summary entries for recent context.
- Private events are excluded from this index.
- Missing daily data should stay missing; do not invent weight, mood, diet, activity, or sleep values.

## 3.2 Source Confidence and Review Memory

Migrated Gemini, NotebookLM, or Obsidian histories are not all equal. v0.1.6 adds:

```text
memory/source_confidence.yaml
memory/open_review_items.yaml
memory/gemini_state_summary.md
```

Rules:

- `report_verified`: backed by a report or health archive, but still preserve source path.
- `user_reported`: useful symptom, habit, weight, mood, or correction signal.
- `gemini_inferred`: discussion clue only; never a medical fact by itself.
- `needs_review`: conflict, stale value, or missing source.
- Raw Gemini chats are not read by default during Obsidian refined-state import.
- Open review items should be resolved by a report, doctor conclusion, or explicit user confirmation before affecting current medical state.

## 4. Working Context

The runtime context is regenerated into:

```text
memory/current_context.md
```

It reads:

- `memory/profile.yaml`
- `memory/current_medical_state.yaml`
- `memory/source_confidence.yaml`
- `memory/open_review_items.yaml`
- official events from `events/events.jsonl`
- recent live events
- promoted low-risk historical imports
- doctor question candidates

Draft imports are excluded from working context until reviewed.

Historical imports are treated conservatively:

- green low-risk imported events can become memory hints
- report, medication, yellow, and red items stay in manual review
- imported AI summaries are not authoritative medical facts

## 5. Generated Artifacts

Artifacts are regenerated from event memory:

```text
daily_logs/YYYY-MM-DD.md
husband_summaries/
baby_diaries/
weekly_reviews/
doctor_questions/
```

Private events are hidden or represented as placeholders in shareable summaries.

## Why This Design

Pregnancy data is high-value and sensitive. The design optimizes for:

- local-first control
- raw data preservation
- upgrade-safe migrations
- traceable medical context
- privacy-aware partner sharing
- compatibility with different message channels

## What v0.1 Does Not Yet Include

v0.1 does not include:

- semantic vector search
- cloud sync
- multi-user hosted accounts
- automatic report OCR
- doctor-grade diagnosis
- full long-term summarization strategy across years

These can be added later without replacing the core event log.

## Install Check

After installation, run:

```bash
PYTHONPATH=src python scripts/install_check.py --data-root /tmp/pregnancy-copilot-install-check
```

This checks whether local memory can be initialized, raw input can be saved, events can be appended, `current_context.md` can be generated, and daily logs can be written.

## Safety Triage Memory

Each event stores the triage result:

- `risk_level`
- `risk_reason`
- `red_flags_detected`
- `doctor_question_candidates`

The triage system has two layers:

- local rules for deterministic red/yellow/green fallback
- optional semantic advisor for LLM-assisted escalation

The semantic layer may upgrade risk but must not downgrade a rule-based red result.

## Rebuild Memory

After imports, manual review, or upgrades, rebuild derived memory:

```bash
PYTHONPATH=src python scripts/rebuild_memory.py \
  --data-root ./pregnancy-data \
  --date 2026-05-05
```

This regenerates:

- `memory/current_context.md`
- `memory/current_medical_state.yaml`
- `memory/medical_timeline.md`
- `memory/emotional_pattern.md`
- `daily_logs/YYYY-MM-DD.md`
