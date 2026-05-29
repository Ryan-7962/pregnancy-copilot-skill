# Runtime Connection Model

Pregnancy Copilot is a skill plus a local Python runtime. A Feishu bot will not reply just because the bot exists.

For a real user-facing pregnancy bot or pregnant-user conversation window, exactly one of these runtime connections must be active:

1. Host Agent Runtime, preferred for Hermes/OpenClaw v0.1.2:

```bash
PYTHONPATH=src .venv/bin/python scripts/process_host_message.py \
  --data-root ./pregnancy-data \
  --channel hermes \
  --conversation-id pregnancy-window \
  --sender-id pregnant-user \
  --sender-role pregnant_user \
  --text "今天肚子有点紧，休息后好了"
```

2. A persistent standalone event loop:

```bash
PYTHONPATH=src .venv/bin/python scripts/run_feishu_event_loop.py \
  --data-root ./pregnancy-data \
  --profile <pregnancy_bot_profile>
```

3. A host Agent such as Hermes/OpenClaw supervising that same event loop as a background worker.

4. A host Agent natively routing the pregnancy bot's Feishu events into this skill's message processor.

5. A host Agent routing default-channel JSON into the generic channel bridge:

```bash
PYTHONPATH=src .venv/bin/python scripts/process_channel_message.py \
  --data-root ./pregnancy-data \
  --json '{"channel":"agent_default","chat_id":"pregnancy-default-chat","sender_id":"pregnant-user","text":"今天肚子有点紧，休息后好了"}'
```

This is the recommended first step for the current test topology: the host Agent's default chat is treated as the pregnant user's conversation entrypoint. WeChat, Feishu, and other gateways remain replaceable adapters.

## What Tests Prove

`scripts/check_feishu_readiness.py` proves the selected `lark-cli` profile has the required local config, auth, event schema, and scopes for the verified P2P path.

`scripts/run_feishu_p2p_smoke_test.py` starts a temporary event loop, sends a test message, verifies local files, and verifies a bot reply. It proves the path can work when the event loop is running.

These tests do not prove that the pregnancy bot is already connected to Hermes/OpenClaw as a persistent 24/7 agent.

`scripts/process_host_message.py` proves the host runtime path: one host Agent can pass a message from a pregnant-user conversation into the skill and receive a reply payload without running a standalone bot loop.

`scripts/process_channel_message.py` proves channel normalization: a host Agent can pass JSON from a non-Feishu gateway into the same Host Runtime without duplicating pregnancy logic in that gateway.

`scripts/run_host_channel_acceptance.py` proves the host default-channel topology: symptom messages are handled with context, ordinary chat passes through, and raw input is stored under `raw_agent_default_messages/`.

## Host Reply Contract

All host runtime paths return `host_action`.

- `type=pass_through`: the message is outside Pregnancy Copilot scope. The host should continue normal conversation handling and should not send `reply_text` from this skill.
- `type=answer_with_context_package`: the skill has stored the message and generated a pregnancy context package. The host should use its own LLM with `context_package`, then send the final answer to `target_channel` / `target_conversation_id`.

`fallback_reply_text` exists for unattended or degraded mode. In normal Hermes/OpenClaw mode, prefer the host LLM answer grounded in `context_package`.

## Default Pregnant-User Bot

The recommended testing topology is:

```text
Pregnant user's Feishu account
  -> pregnancy bot app/profile
  -> persistent event loop or Hermes worker
  -> pregnancy-data/
```

Partner/host Agent channel summary sharing is an optional extension. It should not be required for v0.1 deployment or testing.

If the pregnant user sends a message to the pregnancy bot and gets no reply, check these in order:

1. Is `scripts/run_feishu_event_loop.py` currently running for that bot profile?
2. Is Hermes/OpenClaw supervising that exact worker?
3. Is `--profile` the actual lark-cli profile name, not just a friendly bot name?
4. Does `scripts/check_feishu_readiness.py --profile <profile>` return `ok: true`?
5. Does `scripts/run_feishu_p2p_smoke_test.py --profile <profile> --bot-open-id <bot_open_id>` return `ok: true`?

## Minimal 24/7 Worker Example

On Linux/systemd:

```ini
[Unit]
Description=Pregnancy Copilot Event Loop
After=network.target

[Service]
WorkingDirectory=/opt/pregnancy-copilot
Environment=PYTHONPATH=/opt/pregnancy-copilot/src
ExecStart=/opt/pregnancy-copilot/.venv/bin/python scripts/run_feishu_event_loop.py --data-root /opt/pregnancy-data --profile <lark-profile>
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

If Hermes manages background processes, configure Hermes to run the same command and restart it on failure.

The event loop initializes missing `pregnancy-data/` directories and memory templates at startup. For real use, still run `scripts/init_data_dir.py` first and edit `memory/profile.yaml` before letting a family member use the bot.

Production-oriented templates are kept in:

- `docs/DEPLOYMENT_WORKER.md`
- `docs/HOST_AGENT_RUNTIME.md`
- `ops/docker-compose.worker.yml`
- `ops/pregnancy-copilot.service`
- `ops/run-worker-nohup.sh`
