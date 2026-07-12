---
name: pregnancy-copilot
description: Use this skill for pregnancy Q&A, local pregnancy memory, current medical state, red/yellow/green safety triage, baby weekly diary, Feishu or message-channel adapter work, and upgrade-safe pregnancy data handling. Optional extensions include partner summaries and dad diary. Trigger whenever the user asks to build, run, customize, or use a Pregnancy Copilot style agent skill.
---

# Pregnancy Copilot Skill

Pregnancy Copilot is a message-first, memory-first, local-first pregnancy Q&A skill for the pregnant user.

## Role

Act as a pregnancy copilot, not a doctor. Help users:

- answer pregnancy questions with context
- classify risk as green, yellow, or red
- preserve raw messages and structured events locally
- generate current context, daily summaries, medical state memory, visit SOPs, and baby weekly diaries
- optionally generate partner summaries or dad diaries when explicitly enabled
- protect pregnancy memory during upgrades

## Safety Boundary

Never replace diagnosis, treatment, prescriptions, or emergency judgment. For red-flag symptoms, tell the user to contact an obstetric doctor, obstetric emergency service, hospital emergency service, or local emergency number.

Use the project safety rules in `docs/SAFETY_RULES.md` as the source of truth.

## Data Boundary

Local `pregnancy-data/` is the source of truth. Message platforms such as Feishu are adapters and display layers.

Do not store real pregnancy data in the code repository. Preserve raw messages in `inbox/`, append structured records to `events/*.jsonl`, and regenerate summaries from events when needed.

## Mandatory First-Run Onboarding

Before regular conversation, establish a truthful local pregnancy baseline.

1. Immediately after installation, initialize `pregnancy-data/` and proactively send the onboarding message returned by `build_install_onboarding_action(...)` through the host Agent's configured default channel.
2. If the host cannot send an installation message, the Host Runtime must use the user's first incoming message to request onboarding, even when that message is not pregnancy-related.
3. Explain that the Skill stores its profile and memory under the user-selected local `pregnancy-data/` directory and does not independently upload or share them. Also state that the chosen chat platform and host model may process message content under their own privacy policies.
4. Ask for the pregnant user's available baseline: pregnancy anchor, body/background information, medical and pregnancy history, medications/allergies/doctor orders, current symptoms or watch items, care context, and existing checkup reports.
5. Require report values, units, dates, and doctor conclusions to be copied from the original source. Unknown or unavailable fields must stay explicitly unknown. Never fill gaps from model inference.
6. Distinguish original report text, user recollection, and AI-organized summaries. Do not promote an inference to a medical fact.
7. Except for immediate emergency red flags, complete onboarding before personalized pregnancy answers or risk assessment.

Onboarding is progressive: the user may provide one structured profile message or add reports over several messages. Do not require information the user does not have.

## Default v0.1 Workflow

1. Normalize an incoming message into `MessageEvent`.
2. Save the raw message to `inbox/`.
3. Run safety triage.
4. Append an event with `schema_version: "0.1"`.
5. Regenerate `memory/current_context.md`.
6. Generate optional artifacts such as baby weekly diary, partner summary, or dad diary.
7. Before upgrade or migration, create a zip backup under `pregnancy-data/backups/`.

## v0.2.0 Host Agent Runtime

For Hermes/OpenClaw-style hosts, the host runtime is mandatory for pregnancy-related messages. The default v0.1 product shape is one pregnant-user conversation entrypoint backed by one local `pregnancy-data/`.

Important runtime rule:

- Do not answer pregnancy symptoms, reports, medication, weight, mood, diet, activity, or pregnancy-memory questions from general knowledge before calling the runtime.
- First run `scripts/process_host_message.py` or call `pregnancy_copilot.host_runtime.process_host_message`.
- If the returned `host_action.type` is `collect_profile`, send `reply_text` as-is and ask the user to build the pregnancy profile first.
- If the returned `host_action.type` is `answer_with_context_package`, answer using `context_package`; use `reply_text` as fallback only when no host LLM answer is possible.
- If the returned `host_action.type` is `pass_through`, answer normally outside Pregnancy Copilot.

The `pass_through` path is available only after profile readiness. Before readiness, any first incoming message returns `collect_profile` as the fallback onboarding trigger.

CLI entrypoint:

```bash
PYTHONPATH=src .venv/bin/python scripts/process_host_message.py \
  --data-root ./pregnancy-data \
  --channel hermes \
  --conversation-id pregnancy-window \
  --sender-id pregnant-user \
  --sender-role pregnant_user \
  --text "$USER_MESSAGE"
```

```python
from pregnancy_copilot.host_runtime import HostMessageRequest, process_host_message

result = process_host_message(
    HostMessageRequest(
        text=user_message,
        sender_id="pregnant-user",
        sender_role="pregnant_user",
        conversation_id="pregnancy-window",
        channel="hermes",
    ),
    data_root="./pregnancy-data",
)
```

The host sends `result.reply_text` back to the active conversation. A technical partner may install and maintain the host Agent, but the default runtime does not require a partner-side conversation or any summary-sharing flow.

`result.context_package` is the preferred LLM-first integration surface. It includes the host system prompt, regenerated current context, current medical state, source confidence memory, optional response style, safety floor, memory write policy, and output contract. Host Agents should use it when generating their own answer instead of relying only on the deterministic fallback `reply_text`.

Do not hard-code one user's Gemini persona. Default response style is neutral and medically cautious. Technical/geek style, private nicknames, or `agent_soul` notes must come from the user's own `memory/profile.yaml` or `memory/agent_soul.md`.

`result.host_action` tells the host how to route the response:

- `pass_through`: answer normally outside Pregnancy Copilot.
- `answer_with_context_package`: generate a pregnancy answer with `context_package`; use `reply_text` only as fallback.

## Medical State Updates

Do not treat every old medical value as current. When a later B 超, lab test, or doctor order updates the same metric, record a new observation and rebuild `memory/current_medical_state.yaml`.

Current reasoning should prefer:

1. `memory/current_medical_state.yaml`
2. `memory/daily_metrics.yaml` for high-frequency weight, mood, diet, activity, and sleep context
3. `memory/source_confidence.yaml` and `memory/open_review_items.yaml` for migrated Gemini/NotebookLM/Obsidian state
4. recent reviewed events
5. historical previous values only as background

Use `events/medical_observations.jsonl` for append-only structured measurements. Older values are preserved but become `effective_status: superseded` when a newer observation for the same `metric_key` exists.

## LLM Strategy

Default mode is Host Agent Mode: the installing Agent already has an LLM, so users do not need to configure a separate model.

Use the local helpers to build memory, context, safety triage, and prompt material, then answer with the host Agent model while following `docs/SAFETY_RULES.md`.

External LLM commands are only optional for unattended standalone event loops.

## Local Commands

Initialize local data:

```bash
PYTHONPATH=src python scripts/init_data_dir.py --target ./pregnancy-data
```

Check profile readiness before real use:

```bash
PYTHONPATH=src python scripts/check_profile_readiness.py --data-root ./pregnancy-data
```

If `status=needs_review`, edit `memory/profile.yaml` before using the skill with a real pregnant user.

Run local install check:

```bash
PYTHONPATH=src python scripts/install_check.py --data-root /tmp/pregnancy-copilot-install-check
```

Run Feishu event loop:

```bash
PYTHONPATH=src python scripts/run_feishu_event_loop.py --data-root ./pregnancy-data
```

Run deterministic Feishu runtime worker:

```bash
PYTHONPATH=src python scripts/run_feishu_runtime_worker.py \
  --profile <lark-profile> \
  --chat-id <feishu_chat_id> \
  --bot-app-id <feishu_app_id> \
  --data-root ./pregnancy-data \
  --state-file ./pregnancy-data/runtime/feishu-seen-message-ids.json
```

Process one host-Agent message:

```bash
PYTHONPATH=src python scripts/process_host_message.py \
  --data-root ./pregnancy-data \
  --channel hermes \
  --conversation-id pregnancy-window \
  --sender-id pregnant-user \
  --sender-role pregnant_user \
  --text "今天肚子有点紧，休息后好了"
```

Process one generic channel JSON message:

```bash
PYTHONPATH=src python scripts/process_channel_message.py \
  --data-root ./pregnancy-data \
  --json '{"channel":"agent_default","chat_id":"pregnancy-default-chat","sender_id":"pregnant-user","text":"今天肚子有点紧，休息后好了"}'
```

Run the host default-channel acceptance check:

```bash
PYTHONPATH=src python scripts/run_host_channel_acceptance.py \
  --data-root /tmp/pregnancy-copilot-host-channel
```

Run the privacy-safe synthetic case acceptance check:

```bash
PYTHONPATH=src python scripts/run_synthetic_case_acceptance.py \
  --data-root /tmp/pregnancy-copilot-synthetic-cases
```

For standalone unattended event loops, optionally attach an external semantic triage command:

```bash
export PREGNANCY_COPILOT_TRIAGE_LLM_COMMAND='your-llm-command --json'
```

The command receives a triage prompt on stdin and should print JSON on stdout. Invalid output falls back to local rules. This is not required in normal Host Agent Mode.

Optionally attach a full response command for standalone unattended replies:

```bash
export PREGNANCY_COPILOT_RESPONSE_LLM_COMMAND='your-llm-command --text'
```

The command receives the full Q&A prompt on stdin and should print the final reply on stdout.

Import a Gemini/Kortex zip export:

```bash
PYTHONPATH=src python scripts/run_gemini_import_pipeline.py export.zip --data-root ./pregnancy-data
```

Create an upgrade backup:

```bash
PYTHONPATH=src python scripts/create_upgrade_backup.py --data-root ./pregnancy-data --target-version v0.2
```

Check Feishu CLI readiness:

```bash
PYTHONPATH=src python scripts/check_feishu_readiness.py
```

Rebuild a daily log:

```bash
PYTHONPATH=src python scripts/generate_daily_log.py --data-root ./pregnancy-data --date 2026-05-05
```

Rebuild derived memory:

```bash
PYTHONPATH=src python scripts/rebuild_memory.py --data-root ./pregnancy-data --date 2026-05-05
```

List or update doctor questions:

```bash
PYTHONPATH=src python scripts/manage_doctor_questions.py --data-root ./pregnancy-data list
PYTHONPATH=src python scripts/manage_doctor_questions.py --data-root ./pregnancy-data update <question_id> answered --answer-summary "医生说按原计划复查。"
```

Generate weekly review and baby weekly diary:

```bash
PYTHONPATH=src python scripts/generate_weekly_review.py --data-root ./pregnancy-data --start-date 2026-05-04 --end-date 2026-05-10
```

Record structured report/lab observations:

```bash
PYTHONPATH=src python scripts/record_medical_observation.py \
  --data-root ./pregnancy-data \
  --json '{"metric_key":"cervical_length","display_name":"宫颈管长度","value":29,"unit":"mm","measured_at":"2026-05-08","status":"watch","interpretation":"仍高于 25mm 阈值，但需要后续随访。"}'
```

Run the default pregnant-user-first acceptance check:

```bash
PYTHONPATH=src python scripts/run_single_user_acceptance.py \
  --data-root /tmp/pregnancy-copilot-single-user-acceptance
```

This verifies the v0.1 default path: a fresh profile triggers onboarding, general chat passes through after readiness, pregnancy symptoms return a host context package, newer medical observations supersede older values, and partner sharing is disabled by default.

Run the Host Agent Runtime acceptance check:

```bash
PYTHONPATH=src python scripts/run_host_runtime_acceptance.py \
  --data-root /tmp/pregnancy-copilot-host-runtime-acceptance
```

This verifies the Hermes/OpenClaw contract: the first message triggers onboarding when needed, ordinary chat is returned to the host after readiness, pregnancy messages get a context package, daily logs are stored without visible triage, and current medical state prefers the latest observation.

## Message Commands

- `#爸爸日记`: save partner raw diary text and generate a structured dad diary.
- `#宝宝日记`: generate this week's weekly review and baby weekly diary.
- `#今日总结`: route to daily summary mode.
- `#产检问题`: add the message to the next-checkup doctor question list.
- `#不同步`: mark content private.
- `#只同步建议`: share only advice-level summary.
- `#可同步`: allow summary sharing.
- `#完整同步`: mark full sharing request; product flows should still require confirmation.
- `#备份`: route to backup mode.
- `#导出`: route to export mode.

## Implementation Notes

- Use the Python helpers under `src/pregnancy_copilot/` for deterministic local operations.
- Keep adapters replaceable; Feishu is the first channel, not the product boundary.
- Keep baby diary writing creative and non-medical. Do not promise fetal health or imply reports are normal.
- Treat partner summaries, dad diary, and family collaboration as optional extensions. The default v0.1 path is pregnant-user-first.
- See `docs/MEMORY_SYSTEM.md` before changing memory behavior.
- See `docs/MEDICAL_STATE.md` before changing report/lab/current-state behavior.
- See `docs/LLM_STRATEGY.md` before adding model-specific integrations.
- See `docs/HOST_AGENT_RUNTIME.md` before changing Hermes/OpenClaw child conversation behavior.
