# Hermes Quickstart for Pregnancy Copilot Skill v0.1

This guide is for running Pregnancy Copilot as a reusable local-first skill behind a Feishu/Lark bot.

Important: a Feishu bot is only the message shell. It will reply only when a Pregnancy Copilot event loop is running for that bot profile, or when Hermes/OpenClaw routes that bot's events into this skill.

## Verified v0.1.7 Path

v0.1.7 is verified for:

- Host Agent Runtime calls from a Hermes/OpenClaw-style parent Agent
- Feishu P2P bot chat while the event loop is running
- local Markdown + JSONL memory
- first-run profile onboarding before normal pregnancy Q&A
- deterministic green/yellow/red safety floor after profile readiness
- doctor question list
- baby weekly diary command
- optional standalone LLM command hooks
- direct Feishu runtime worker for tests where the host Agent should not paraphrase the runtime fallback

v0.1 does not yet claim group chat event support. Group messages need separate Feishu console event/scope validation.

## 1. Install

Requirements:

- Python 3.10+
- `lark-cli >= 1.0.23`

```bash
python3.11 -m venv .venv  # or any Python >= 3.10
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e .
.venv/bin/python -m pip install pytest
```

Check CLI version and config:

```bash
lark-cli doctor
```

If you upgraded from an older CLI and config is not found, run:

```bash
lark-cli profile list
lark-cli config show
```

Then either re-run `lark-cli config init` for the intended workspace/profile, or copy the old app config into the new profile location after checking it contains no stale token or wrong app.

## 2. Initialize Data

The event loop also initializes missing directory/templates on startup, but explicit initialization is recommended before first use so you can edit `profile.yaml`.

```bash
PYTHONPATH=src .venv/bin/python scripts/init_data_dir.py --target ./pregnancy-data
```

Edit:

```text
pregnancy-data/memory/profile.yaml
```

Set `current_gestational_age`, `baby_nickname`, hospital context, and privacy defaults.

Check readiness:

```bash
PYTHONPATH=src .venv/bin/python scripts/check_profile_readiness.py \
  --data-root ./pregnancy-data
```

If it returns `needs_review`, do not start real family use yet. Update `memory/profile.yaml` first.

If you deliberately want the pregnant user to complete onboarding from the chat window, leave the template in place. The Host Runtime will save the first raw message and ask for baseline profile/latest report data before answering normal symptom questions. Immediate red-flag emergencies still bypass onboarding and return emergency guidance.

## 3. Check Feishu Readiness

```bash
PYTHONPATH=src .venv/bin/python scripts/check_feishu_readiness.py
```

With a named Feishu app/profile:

```bash
PYTHONPATH=src .venv/bin/python scripts/check_feishu_readiness.py --profile <lark-profile>
```

For v0.1, expected:

- `ok: true`
- `capabilities.p2p_event_receive.ok: true`
- `capabilities.user_send_message.ok: true` if you want CLI-driven smoke tests
- `capabilities.group_event_receive.ok: false` is acceptable

## 4. Run Real P2P Smoke Test

Find the bot open_id. One way is to inspect a bot chat:

```bash
lark-cli im +chat-messages-list --as user --chat-id <p2p_chat_id> --page-size 5 --sort desc --format json
```

Then run:

```bash
PYTHONPATH=src .venv/bin/python scripts/run_feishu_p2p_smoke_test.py \
  --data-root /tmp/pregnancy-copilot-feishu-p2p-smoke \
  --bot-open-id <bot_open_id> \
  --profile <lark-profile>
```

Success means:

- `ok: true`
- `risk_level: green`
- `local_files.events_jsonl: true`
- `local_files.raw_message: true`
- `local_files.daily_log: true`
- `bot_reply.ok: true`

## 5. Connect the Bot or Window to a Runtime

`readiness` and `smoke` are not the same as a persistent Hermes connection. For actual pregnant-user testing, the pregnancy bot profile must be attached to one active runtime.

### Hermes Feishu bot-only binding

If the pregnant-user channel is a Hermes-managed Feishu bot, bind `lark-cli` to the same Hermes app in bot-only mode:

```bash
lark-cli config bind --source hermes --app-id <feishu_app_id> --identity bot-only
```

When checking or using that Hermes app through `lark-cli`, set `HERMES_HOME` so the CLI reads the Hermes workspace:

```bash
HERMES_HOME=~/.hermes lark-cli config show
HERMES_HOME=~/.hermes lark-cli doctor
```

Hermes pairing approval is not always enough for Feishu interactive command approval cards. If button clicks are logged as unauthorized, add the operator open_id to `~/.hermes/.env` and restart the gateway:

```bash
FEISHU_ALLOWED_USERS=<operator_open_id>
hermes gateway restart
```

Then send a pregnancy test message and verify that the host Agent invokes `pregnancy-copilot` and writes `pregnancy-data/events/events.jsonl`.

Option A (preferred): Hermes/OpenClaw receives the pregnant-user message and calls the Host Agent Runtime:

```bash
PYTHONPATH=src .venv/bin/python scripts/process_host_message.py \
  --data-root ./pregnancy-data \
  --channel hermes \
  --conversation-id pregnancy-window \
  --sender-id pregnant-user \
  --sender-role pregnant_user \
  --text "今天肚子有点紧，休息后好了"
```

The host sends `reply_text` back to that conversation. This makes the pregnancy window a conversation entrypoint of the host Agent, not a separate product.

Option B: Hermes supervises the event loop as a long-running worker.

```bash
PYTHONPATH=src .venv/bin/python scripts/run_feishu_event_loop.py \
  --data-root ./pregnancy-data \
  --profile <lark-profile>
```

Option C: deterministic Feishu runtime worker.

Use this when testing a fresh bot and you need exact runtime behavior instead of a host Agent paraphrase. First mark visible history as already seen, then start the worker:

```bash
PYTHONPATH=src .venv/bin/python scripts/run_feishu_runtime_worker.py \
  --profile <lark-profile> \
  --chat-id <feishu_chat_id> \
  --bot-app-id <feishu_app_id> \
  --data-root ./pregnancy-data \
  --state-file ./pregnancy-data/runtime/feishu-seen-message-ids.json \
  --mark-existing

PYTHONPATH=src .venv/bin/python scripts/run_feishu_runtime_worker.py \
  --profile <lark-profile> \
  --chat-id <feishu_chat_id> \
  --bot-app-id <feishu_app_id> \
  --data-root ./pregnancy-data \
  --state-file ./pregnancy-data/runtime/feishu-seen-message-ids.json
```

If Hermes gateway is also replying to the same bot, stop one of the two runtimes before testing to avoid duplicate replies.

Option D: run either worker under `systemd`, Docker, `supervisord`, or another process manager.

Option E: Hermes/OpenClaw natively routes Feishu events from the pregnancy bot into this skill. In that mode, ensure the routed events still enter the same storage and safety pipeline.

If you send a message to the bot and get no reply, the most likely cause is that no persistent event loop is currently attached to that bot profile.

For reusable deployment templates, see:

- `docs/DEPLOYMENT_WORKER.md`
- `docs/HOST_AGENT_RUNTIME.md`
- `ops/docker-compose.worker.yml`
- `ops/pregnancy-copilot.service`
- `ops/run-worker-nohup.sh`

## Pregnant-User-First Channel Model

The recommended v0.1 deployment is:

```text
Pregnant user -> pregnancy bot/profile such as <lark-profile> -> pregnancy-data/
```

A partner or family member may install and maintain the skill, but that does not imply consent to read all pregnancy records. Default sharing should be private until the pregnant user enables summary or full sharing.

## 6. Message Commands

```text
今天肚子有点紧，休息后好了，没有流血也没有流水
#产检问题 下次产检要不要问宫颈长度？
#宝宝日记
#只同步建议 今天有点焦虑，想要一些陪伴建议
```

Optional partner extensions can still support commands such as `#爸爸日记`, but they are not required for the default v0.1 setup.

## 7. Optional Standalone LLM Hooks

Most Hermes/OpenClaw-style hosts already have a model. In that host-agent mode, no extra model config is required.

Only set these for unattended Python auto-replies:

```bash
export PREGNANCY_COPILOT_TRIAGE_LLM_COMMAND='your-llm-command --json'
export PREGNANCY_COPILOT_RESPONSE_LLM_COMMAND='your-llm-command --text'
```

The rule layer remains active. Semantic triage may upgrade risk, but must not downgrade local red flags.

## 8. Backup Before Upgrade

```bash
PYTHONPATH=src .venv/bin/python scripts/create_upgrade_backup.py \
  --data-root ./pregnancy-data \
  --target-version v0.2
```

Do this before changing code or migrating memory.
