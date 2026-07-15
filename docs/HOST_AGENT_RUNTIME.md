# Host Agent Runtime v0.2.1

## Purpose

The Host Runtime is the model- and channel-neutral integration surface for Hermes, OpenClaw, Codex, Claude Code, and similar Agents.

The host already has an LLM. Pregnancy Copilot does not require another model API. It returns local context, semantic instructions, memory policy, and a deterministic fallback.

## Single-Pregnancy Call

```python
from pregnancy_copilot.host_runtime import HostMessageRequest, process_host_message

result = process_host_message(
    HostMessageRequest(
        text=user_message,
        sender_id=trusted_sender_id,
        conversation_id=trusted_conversation_id,
        channel=trusted_channel,
        message_id=original_message_id,
        event_id=original_event_id,
    ),
    data_root="./pregnancy-data",
)
```

The first endpoint is bound to that data root. A different sender/channel/conversation is rejected until explicitly authorized.

## Multi-Pregnancy Call

```python
request = HostMessageRequest(
    text=user_message,
    sender_id=trusted_sender_id,
    conversation_id=trusted_conversation_id,
    channel=trusted_channel,
    message_id=original_message_id,
    pregnancy_id="pregnancy-a",
)
result = process_host_message(request, data_root="./pregnancy-data-root")
```

`pregnancy_id` is trusted host configuration. Never copy it from an untrusted message payload. The runtime stores each identity under `identities/<pregnancy_id>/` and rejects unbound endpoints that try to claim an existing identity.

To authorize another endpoint deliberately:

```python
from pregnancy_copilot.identity import IdentityEndpoint, IdentityRegistry

IdentityRegistry("./pregnancy-data-root").bind_endpoint(
    "pregnancy-a",
    IdentityEndpoint(
        channel="another_channel",
        conversation_id="pregnancy-a-mobile",
        sender_id="pregnant-user-a-mobile",
    ),
)
```

## Result Actions

### `collect_profile`

Used when no pregnancy time anchor exists. Send `reply_text` and continue progressive onboarding. Missing optional fields may remain unknown.

An explicit emergency red flag bypasses this gate; urgent guidance uses unknown context and never template facts.

### `answer_with_context_package`

Used for every valid message in the configured pregnant-user entrypoint after readiness.

The host must:

1. read `context_package.semantic_routing_contract`;
2. decide pregnancy and medical relevance semantically;
3. show red/yellow/green only when medically relevant;
4. avoid a medical event for ordinary chat;
5. use `current_medical_state.metrics.*.current` before historical values;
6. say unknown or ask for source data instead of guessing;
7. use `reply_text` only as a deterministic fallback.

Ordinary chat still receives minimum context because otherwise diet, travel, body-change, and colloquial pregnancy questions can be missed by a keyword router. Context injection does not mean triage or durable medical extraction.

## Context Package

```text
system_prompt
context_markdown
current_medical_state
profile_readiness
response_style
safety_floor
semantic_routing_contract
memory_write_policy
output_contract
```

The package states that the host LLM owns semantic judgment. If no host LLM is available, the runtime may return deterministic fallback text but must not claim a completed semantic review.

## Idempotency

- Prefer original channel `event_id`.
- Otherwise prefer original `message_id`.
- If both are missing, the runtime derives a stable ID from channel, conversation, sender, timestamp, message type, and content.
- A duplicate ID is written once.
- Two different message IDs sent in the same second are both retained.

## Generic JSON Bridge

```bash
PYTHONPATH=src python scripts/process_channel_message.py \
  --data-root ./pregnancy-data \
  --json '{"channel":"agent_default","chat_id":"pregnancy-chat","sender_id":"pregnant-user","message_id":"msg-1","text":"Pregnancy question"}'
```

For multiple identities, pass `--pregnancy-id` as a CLI/configuration argument. A `pregnancy_id` inside the JSON payload is ignored.

## Failure Behavior

- Host semantic provider exception/refusal/invalid JSON: deterministic fallback, no semantic-completion claim.
- Explicit rule red cannot be downgraded by an optional advisor.
- Unsafe source/path component: reject before writing.
- Unbound identity endpoint: reject before reading or writing pregnancy files.
- Duplicate delivery: idempotent raw/event/observation writes.

## Acceptance

```bash
PYTHONPATH=src .venv/bin/python scripts/run_host_runtime_acceptance.py \
  --data-root /tmp/pregnancy-copilot-host-runtime-acceptance

PYTHONPATH=src .venv/bin/python scripts/run_host_channel_acceptance.py \
  --data-root /tmp/pregnancy-copilot-host-channel-acceptance
```
