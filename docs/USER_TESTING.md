# User Testing: v0.3.0 Public Alpha

Use fictional data only. Do not paste real names, addresses, account IDs, reports, or private chat exports into public issues.

## Automated Suite

```bash
.venv/bin/python -m pytest -q
```

The v0.3.0 adversarial coverage includes:

- answer-first onboarding, tutorial progression, skip/resume, and no-record controls;
- daily consolidation, private placeholders, and idempotent daily indexes;
- prenatal schedule history, source separation, and one-time reminder claims;

- pregnancy diet/travel questions that have no old router keyword;
- ordinary chat with context but no triage/event;
- negation, later-clause bleeding, and reduced fetal movement variants;
- emergency messages before profile readiness;
- LMP-only and progressive onboarding;
- dynamic gestational age;
- undated and low-confidence medical candidates;
- current/history/provenance rendering;
- duplicate and concurrent message/observation delivery;
- identity isolation and endpoint authorization;
- path traversal;
- host LLM failure/refusal/invalid output;
- backup verification, restore, and migration;
- release privacy scanning.

## Runtime Acceptance

```bash
PYTHONPATH=src .venv/bin/python scripts/run_single_user_acceptance.py \
  --data-root /tmp/pregnancy-copilot-single-user-acceptance

PYTHONPATH=src .venv/bin/python scripts/run_host_runtime_acceptance.py \
  --data-root /tmp/pregnancy-copilot-host-runtime-acceptance

PYTHONPATH=src .venv/bin/python scripts/run_host_channel_acceptance.py \
  --data-root /tmp/pregnancy-copilot-host-channel

PYTHONPATH=src .venv/bin/python scripts/run_synthetic_case_acceptance.py \
  --data-root /tmp/pregnancy-copilot-synthetic-cases
```

Each command must return `"ok": true`.

## Expected Conversation Contract

### Fresh installation

The host proactively sends a non-blocking onboarding welcome when possible. Otherwise the first incoming message returns `answer_with_context_package` plus one optional `tutorial_nudge`.

Users may provide LMP, EDD, or dated gestational age first and add optional fields later. Unknown fields remain unknown.

### Ordinary chat

Expected:

```text
handled=true
intent=pregnancy_context
risk_level=not_applicable
event=null
host_action.type=answer_with_context_package
```

The host answers normally. It does not show red/yellow/green or write a medical event.

### Pregnancy/medical message

The host reads `semantic_routing_contract`, current medical state, current context, and safety floor. A risk label appears only when medically relevant.

### New report value

- valid date plus sufficient source confidence: may become `current`;
- older eligible values: remain in `previous_values`;
- missing date or low confidence: remain in `candidates`;
- no write-tool success: the answer must not claim that the value was recorded.

### Immediate red flag before onboarding

Urgent guidance is returned without waiting for profile completion. Gestational age, hospital, and other missing facts remain `unknown`; no demo value may appear.

## Multi-Identity Test

Pass `pregnancy_id` as trusted host configuration, not inside the message JSON:

```bash
PYTHONPATH=src .venv/bin/python scripts/process_channel_message.py \
  --data-root /tmp/pregnancy-copilot-multi \
  --pregnancy-id pregnancy-a \
  --json '{"channel":"agent_default","chat_id":"chat-a","sender_id":"user-a","text":"建档：LMP 2026-05-01"}'
```

A second identity must use a different `pregnancy_id`. Attempting to reuse an existing identity from an unbound endpoint must fail before reading or writing that identity's files.

## Upgrade Test

```bash
PYTHONPATH=src .venv/bin/python scripts/upgrade_to_v021.py \
  --data-root /tmp/pregnancy-data-v020-copy
```

Confirm the backup exists, `verify_upgrade_backup` passes, the migration report states that ZIP is unencrypted by default, and the backup restores into an empty directory.

## Real Channel Test

Use the host Agent's configured default channel first. Feishu/Lark is optional. A bot account without an attached running host/worker does not prove runtime connectivity.

Record only anonymized outcomes:

- host and version;
- channel type;
- input category, not private text;
- expected/actual intent and risk behavior;
- whether current/history/candidate memory changed correctly;
- any error without credentials or identifiers.
