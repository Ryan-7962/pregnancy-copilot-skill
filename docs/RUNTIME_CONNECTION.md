# Runtime Connection

## Preferred Topology

```text
Pregnant user's configured chat entrypoint
  -> existing host Agent and LLM
  -> generic Host Runtime request
  -> identity-bound local pregnancy-data
  -> context package
  -> host LLM final answer
```

Channel adapters only normalize message fields. They do not own pregnancy logic.

## Required Trusted Fields

- `channel`
- `conversation_id`
- `sender_id`
- original `message_id` and/or `event_id`
- optional host-configured `pregnancy_id`

Do not accept `pregnancy_id` from the user message payload. The generic bridge takes it as a separate host/CLI argument.

## Actions

- `collect_profile`: send the onboarding response and continue progressive intake.
- `answer_with_context_package`: let the host LLM classify semantic relevance and answer with local context.

The configured pregnant-user entrypoint does not use keyword-based `pass_through` for valid messages. Ordinary chat still uses `answer_with_context_package`, but the host must omit medical triage and medical-state writes when semantic relevance is false.

## Channel-Neutral Example

```bash
PYTHONPATH=src python scripts/process_channel_message.py \
  --data-root ./pregnancy-data \
  --json '{"channel":"agent_default","chat_id":"pregnancy-chat","sender_id":"pregnant-user","message_id":"msg-1","text":"Can I take a flight while pregnant?"}'
```

## Optional Adapters

- host Agent default conversation: recommended minimum integration;
- Feishu/Lark CLI: most tested optional adapter;
- WeChat or other gateways: supported when the host can normalize incoming messages;
- standalone event loop: advanced mode, requires its own optional LLM command for semantic answers.

## Operational Requirement

A bot account alone does not connect to an LLM. Hermes/OpenClaw or a worker must be running and must call the Host Runtime. Smoke tests prove only the tested connection window, not 24/7 supervision.
