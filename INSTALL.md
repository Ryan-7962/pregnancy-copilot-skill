# Pregnancy Copilot Skill v0.1.7 Install Guide

This guide is for public testers who receive the zip package or clone the GitHub repository.

Pregnancy Copilot is a reusable Agent skill, not a standalone app. The normal path is:

```text
pregnant user chat window
  -> Hermes / OpenClaw / Codex / Claude Code host Agent
  -> Pregnancy Copilot Skill
  -> local pregnancy-data/
```

The host Agent supplies the LLM. This skill supplies durable pregnancy memory, current medical state, safety floor, artifacts, and channel adapters.

Default personalization is neutral. If a user wants a special style or an existing Agent soul, configure `preferences.response_style` in `memory/profile.yaml`; do not reuse another user's Gemini boot prompt as the default.

## 1. Requirements

- Python 3.10+
- `pytest` for local verification
- Optional: `lark-cli` if you want Feishu/Lark bot testing

Recommended local setup:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e .
.venv/bin/python -m pip install pytest
```

## 2. Verify The Package

Run the unit test suite:

```bash
.venv/bin/python -m pytest -q
```

Run the single-user acceptance check:

```bash
PYTHONPATH=src .venv/bin/python scripts/run_single_user_acceptance.py \
  --data-root /tmp/pregnancy-copilot-single-user-acceptance
```

Expected: output contains `"ok": true`.

This check proves the default v0.1 path:

- normal chat returns `handled=false`;
- pregnancy symptom messages return a host `context_package`;
- newer medical observations supersede older values in current state;
- partner sharing is disabled by default;
- the pregnant user's own local summaries remain readable.

Run the Host Agent Runtime acceptance check:

```bash
PYTHONPATH=src .venv/bin/python scripts/run_host_runtime_acceptance.py \
  --data-root /tmp/pregnancy-copilot-host-runtime-acceptance
```

Expected: output contains `"ok": true`.

This check proves the Hermes/OpenClaw-style host contract:

- non-pregnancy chat returns `handled=false`;
- pregnancy symptom messages return `context_package`;
- daily logs are stored without visible red/yellow/green triage;
- later medical observations become current;
- inbox, events, current context, and current medical state files are written.

## 3. Initialize Local Pregnancy Data

Create a local data directory:

```bash
PYTHONPATH=src .venv/bin/python scripts/init_data_dir.py --target ./pregnancy-data
```

Edit:

```text
pregnancy-data/memory/profile.yaml
```

Set the pregnancy anchor fields, current focus, hospital context, and privacy defaults.

Do not commit `pregnancy-data/`. It is personal medical memory.

Check whether the profile still contains template values:

```bash
PYTHONPATH=src .venv/bin/python scripts/check_profile_readiness.py \
  --data-root ./pregnancy-data
```

If it returns `status=needs_review`, edit `pregnancy-data/memory/profile.yaml` before real use. This prevents the host model from treating example hospital, example gestational age, or template identity fields as facts.

Alternatively, let the user send a clear first message starting with something like `建档信息：...`. The Host Runtime can fill the core profile fields from structured text and append initial report observations such as NT, CRL, fetal heart rate, and placenta position. Extracted report values are marked as onboarding excerpts and should still be checked against the original report when available.

## 4. Host Agent Integration

For Hermes/OpenClaw-style usage, call the Host Agent Runtime from the existing Agent:

```bash
PYTHONPATH=src .venv/bin/python scripts/process_host_message.py \
  --data-root ./pregnancy-data \
  --channel hermes \
  --conversation-id pregnancy-window \
  --sender-id pregnant-user \
  --sender-role pregnant_user \
  --text "今天肚子有点紧，休息后好了，没有流血也没有流水"
```

The JSON output includes:

- `handled`
- `reply_text`
- `intent`
- `risk_level`
- `context_package`
- `event_id`
- `privacy_level`
- `artifacts`
- `host_action`

Recommended host behavior:

- If `host_action.type=pass_through`, answer using the host Agent's normal chat flow.
- If `host_action.type=collect_profile`, send `reply_text` as-is. Do not answer the symptom/report yet unless it is an immediate red-flag emergency.
- If `host_action.type=answer_with_context_package`, use `context_package` as the LLM context and send the final answer back to `host_action.target_conversation_id`.
- Prefer `current_medical_state.metrics.*.current` over older event history.
- Write new report/lab values through `scripts/record_medical_observation.py`.

See `docs/HOST_AGENT_RUNTIME.md`.

For channels that already produce JSON, use the generic channel bridge:

```bash
PYTHONPATH=src .venv/bin/python scripts/process_channel_message.py \
  --data-root ./pregnancy-data \
  --json '{"channel":"agent_default","chat_id":"pregnancy-default-chat","sender_id":"pregnant-user","text":"今天肚子有点紧，休息后好了"}'
```

The bridge maps common fields into the Host Runtime request. For current testing, treat the host Agent's default chat as the pregnant user's conversation entrypoint. Feishu, WeChat, and other channels are replaceable gateways, not the skill's product boundary.

## 5. Optional Feishu/Lark Testing

Feishu is a channel adapter, not the product boundary.

Check CLI readiness:

```bash
PYTHONPATH=src .venv/bin/python scripts/check_feishu_readiness.py
```

Run a temporary event loop:

```bash
PYTHONPATH=src .venv/bin/python scripts/run_feishu_event_loop.py \
  --data-root ./pregnancy-data
```

With a named Feishu profile:

```bash
PYTHONPATH=src .venv/bin/python scripts/run_feishu_event_loop.py \
  --profile <lark-profile> \
  --data-root ./pregnancy-data
```

For deterministic bot testing, especially when the host Agent tends to paraphrase skill output, run the direct runtime worker. It reads new Feishu user messages, calls the Host Runtime, and replies with `reply_text` exactly:

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

Important: a Feishu bot will not reply unless a host Agent or event loop is actually attached and running.

See `docs/HERMES_QUICKSTART.md` and `docs/USER_TESTING.md`.

## 6. Medical Safety Boundary

This skill is not a doctor, hospital, diagnosis engine, prescription tool, or emergency service.

For bleeding, fluid leakage, severe abdominal pain, fainting, obvious reduced fetal movement after the relevant gestational stage, fever, severe headache/vision symptoms, or any rapidly worsening condition, contact an obstetric doctor, obstetric emergency service, hospital emergency service, or local emergency number.

The host model should use medical sources and local clinical guidance when giving advice. The skill's deterministic layer is only a safety floor and memory substrate.

## 7. Privacy Boundary

Default v0.1.7 is pregnant-user-first:

- The pregnant user owns the data.
- A technical partner may install the skill and channel, but partner access is not automatic consent.
- Partner summary and dad diary are optional extensions.
- Full sharing should require explicit pregnant-user consent.

Never publish:

- `pregnancy-data/`
- `docs/private/`
- real Feishu exports
- real Gemini/Kortex exports
- `.env`
- local virtual environments

## 8. Backup Before Upgrade

Before changing versions or running migrations:

```bash
PYTHONPATH=src .venv/bin/python scripts/create_upgrade_backup.py \
  --data-root ./pregnancy-data \
  --target-version v0.2
```

Backups are written under:

```text
pregnancy-data/backups/
```
