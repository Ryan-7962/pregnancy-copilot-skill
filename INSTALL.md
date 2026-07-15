# Pregnancy Copilot Skill v0.2.1 Install Guide

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

This check proves the default v0.2.1 path after profile onboarding:

- normal chat receives the minimal pregnancy context without triage or a medical event;
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

- a fresh profile triggers onboarding on the first incoming message;
- ordinary chat returns `answer_with_context_package` but does not require a risk label or medical-state write;
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

The recommended path is progressive onboarding through the host Agent. LMP, EDD, or a dated gestational age is the only blocking anchor; other unavailable fields remain unknown and can be added later.

Do not commit `pregnancy-data/`. It is personal medical memory.

Check whether the profile has a pregnancy time anchor:

```bash
PYTHONPATH=src .venv/bin/python scripts/check_profile_readiness.py \
  --data-root ./pregnancy-data
```

If it returns `status=needs_review`, provide LMP, EDD, or a dated current gestational age. The v0.2.1 template contains no realistic hospital, gestational-age, or medical-focus examples.

### Required first-run message

After installation, the host Agent should proactively send the user the result of:

```python
from pregnancy_copilot.host_runtime import build_install_onboarding_action

action = build_install_onboarding_action(
    data_root="./pregnancy-data",
    channel="agent_default",
    conversation_id="pregnancy-window",
)
# Send action["reply_text"] through the host Agent's configured channel.
```

If the host does not support proactive messages, no extra integration is required: before the profile is ready, `process_host_message(...)` converts the first incoming message into `host_action.type=collect_profile`, including ordinary chat.

The message explains the actual privacy boundary: structured memory remains under the local `pregnancy-data/` directory and the Skill does not independently upload it, while the selected chat platform and host model may still process the messages. Users should copy medical values, units, dates, and doctor conclusions from original reports; unknown information stays unknown.

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

- If `host_action.type=collect_profile`, send `reply_text` as-is. Do not answer the symptom/report yet unless it is an immediate red-flag emergency.
- If `host_action.type=answer_with_context_package`, first classify semantic medical relevance with the host LLM, then answer using `context_package`. Ordinary chat receives no risk label and no medical-state write.
- Prefer `current_medical_state.metrics.*.current` over older event history.
- Write new report/lab values through `scripts/record_medical_observation.py`.
- On a fresh profile, do not bypass `collect_profile` with the host Agent's general answer path.

See `docs/HOST_AGENT_RUNTIME.md`.

For channels that already produce JSON, use the generic channel bridge:

```bash
PYTHONPATH=src .venv/bin/python scripts/process_channel_message.py \
  --data-root ./pregnancy-data \
  --json '{"channel":"agent_default","chat_id":"pregnancy-default-chat","sender_id":"pregnant-user","text":"今天肚子有点紧，休息后好了"}'
```

The bridge maps common fields into the Host Runtime request. For current testing, treat the host Agent's default chat as the pregnant user's conversation entrypoint. Feishu, WeChat, and other channels are replaceable gateways, not the skill's product boundary.

For a host that manages multiple pregnant users, configure `pregnancy_id` outside the untrusted message payload:

```bash
PYTHONPATH=src .venv/bin/python scripts/process_channel_message.py \
  --data-root ./pregnancy-data-root \
  --pregnancy-id pregnancy-a \
  --json '{"channel":"agent_default","chat_id":"pregnancy-a-chat","sender_id":"pregnant-user-a","text":"建档：LMP 2026-05-01"}'
```

Each identity receives an independent directory under `identities/`. A different sender/channel/conversation cannot claim an existing identity without explicit endpoint binding.

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

## 6. Visit SOPs

Generate a pre-visit doctor discussion SOP:

```bash
PYTHONPATH=src .venv/bin/python scripts/generate_pre_visit_sop.py \
  --data-root ./pregnancy-data \
  --date 2026-05-22 \
  --lookback-days 14
```

Generate a post-visit action SOP from doctor notes:

```bash
PYTHONPATH=src .venv/bin/python scripts/generate_post_visit_sop.py \
  --data-root ./pregnancy-data \
  --date 2026-05-22 \
  --text "医生说继续观察，下次两周后复查 B 超。每天记录腹痛和出血情况。"
```

These files are local organization aids. They do not replace the doctor's original judgment, and they do not automatically overwrite structured medical observations.

## 7. Medical Safety Boundary

This skill is not a doctor, hospital, diagnosis engine, prescription tool, or emergency service.

For bleeding, fluid leakage, severe abdominal pain, fainting, obvious reduced fetal movement after the relevant gestational stage, fever, severe headache/vision symptoms, or any rapidly worsening condition, contact an obstetric doctor, obstetric emergency service, hospital emergency service, or local emergency number.

The host model should use medical sources and local clinical guidance when giving advice. The skill's deterministic layer is only a safety floor and memory substrate.

## 8. Privacy Boundary

Default v0.2.1 is pregnant-user-first:

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

## 9. Backup Before Upgrade

Before changing versions or running migrations:

```bash
PYTHONPATH=src .venv/bin/python scripts/create_upgrade_backup.py \
  --data-root ./pregnancy-data \
  --target-version v0.2.1
```

Backups are written under:

```text
pregnancy-data/backups/
```

The ZIP is local but not encrypted by default. Protect it with operating-system disk encryption and file permissions. v0.2.0 users can run the verified migration flow:

```bash
PYTHONPATH=src .venv/bin/python scripts/upgrade_to_v021.py \
  --data-root ./pregnancy-data
```

The command creates and verifies a backup before changing derived state. It clears old demo values only when the entire unedited v0.2.0 template matches; partially customized profiles are preserved and listed for manual review.
