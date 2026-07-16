# Hermes / OpenClaw Quickstart v0.3.0

## Install

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -e . pytest
.venv/bin/python -m pytest -q
PYTHONPATH=src .venv/bin/python scripts/init_data_dir.py --target ./pregnancy-data
```

The installing Agent should proactively send `build_install_onboarding_action(...)`. If it cannot, the first incoming message uses answer-first onboarding with one optional tutorial nudge.

## Connect The Existing Host LLM

For every valid message in the configured pregnant-user entrypoint:

1. normalize channel fields into `HostMessageRequest`;
2. preserve original message/event IDs;
3. call `process_host_message`;
4. for `answer_with_context_package`, let the host LLM classify semantic relevance and answer with `context_package`;
5. append `tutorial_nudge` after the main answer when present;
6. show red/yellow/green only for medical relevance.

No additional LLM API is required.

```bash
PYTHONPATH=src .venv/bin/python scripts/process_host_message.py \
  --data-root ./pregnancy-data \
  --channel agent_default \
  --conversation-id pregnancy-window \
  --sender-id pregnant-user \
  --message-id original-message-id \
  --text "怀孕可以坐飞机吗？"
```

## Multiple Pregnant Users

Use one trusted `pregnancy_id` per user:

```bash
PYTHONPATH=src .venv/bin/python scripts/process_channel_message.py \
  --data-root ./pregnancy-data-root \
  --pregnancy-id pregnancy-a \
  --json '{"channel":"agent_default","chat_id":"chat-a","sender_id":"user-a","message_id":"msg-a","text":"建档：LMP 2026-05-01"}'
```

Do not take `pregnancy_id` from the JSON payload. Additional endpoints require explicit `IdentityRegistry.bind_endpoint(...)` authorization.

## Privacy

Local `pregnancy-data/` is the source of truth. The chat gateway, host model, host operator, filesystem permissions, and backups remain separate privacy boundaries. Backups are not encrypted by default.

## Verify

```bash
PYTHONPATH=src .venv/bin/python scripts/run_host_runtime_acceptance.py \
  --data-root /tmp/pregnancy-copilot-host-runtime

PYTHONPATH=src .venv/bin/python scripts/run_host_channel_acceptance.py \
  --data-root /tmp/pregnancy-copilot-host-channel
```
