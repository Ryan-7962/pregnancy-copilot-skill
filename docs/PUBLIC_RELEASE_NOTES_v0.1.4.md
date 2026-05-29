# Public Release Notes v0.1.4

Pregnancy Copilot Skill v0.1.4 is the first handoff package suitable for external technical testing with Hermes/OpenClaw-style host Agents.

## What It Is

Pregnancy Copilot is a reusable local-first Agent skill for pregnancy Q&A and long-term pregnancy memory.

It is not a standalone app. A host Agent receives the user's message, calls the skill, and uses the returned context package to answer with its own LLM.

## Default User Model

v0.1.4 is pregnant-user-first:

- the pregnant user is the first user and data owner;
- a partner or family member may install the host Agent and channel;
- partner summaries, dad diary, and family collaboration are optional extensions;
- partner sharing is private by default.

## Main Capabilities

- Creates the local `pregnancy-data/` directory structure.
- Checks whether `memory/profile.yaml` still contains template values before real use.
- Saves raw incoming messages under `inbox/`.
- Appends structured events to JSONL.
- Regenerates `memory/current_context.md`.
- Records structured medical observations.
- Regenerates `memory/current_medical_state.yaml`.
- Preserves old medical values while marking superseded values as historical.
- Regenerates `memory/daily_metrics.yaml` and `memory/daily_metrics.md` for high-frequency weight, mood, diet, activity, and sleep summaries.
- Returns a Host Agent `context_package` for LLM-first answers.
- Returns an explicit `host_action` envelope so gateways know whether to pass through or answer with context.
- Normalizes host Agent default channel-style channel JSON into Host Runtime requests.
- Supports red/yellow/green safety floor only when medically relevant.
- Generates daily logs, doctor questions, weekly review, and baby weekly diary artifacts.
- Provides optional Feishu/Lark CLI adapter and worker templates.
- Creates upgrade backups before migrations.
- Builds a privacy-filtered release package that excludes private local data.

## What Changed In v0.1.4

- Moved the product shape away from heavy deterministic routing and toward LLM-first host-Agent reasoning.
- Kept deterministic rules as a narrow safety floor instead of forcing every message through medical triage.
- Added current medical state versioning so later report/lab values supersede older ones.
- Added daily metrics indexing so the host model can read recent weight and mood trends without scanning raw conversations.
- Added single-user acceptance testing for the default pregnant-user flow.
- Added Host Runtime acceptance testing for Hermes/OpenClaw-style integration.
- Added privacy-safe synthetic pregnancy cases for public regression testing without private source records.
- Added a generic channel JSON bridge, with current validation focused on host Agent default channel as the pregnant-user Agent channel.
- Added explicit host reply actions: `pass_through` for ordinary chat and `answer_with_context_package` for pregnancy messages.
- Clarified that Feishu bots are channels; the runtime still needs Hermes/OpenClaw/event-loop attachment.
- Made partner-facing sharing optional and private by default.

## Verified Checks

The package should pass:

```bash
.venv/bin/python -m pytest -q
```

```bash
PYTHONPATH=src .venv/bin/python scripts/run_single_user_acceptance.py \
  --data-root /tmp/pregnancy-copilot-single-user-acceptance
```

```bash
PYTHONPATH=src .venv/bin/python scripts/run_host_runtime_acceptance.py \
  --data-root /tmp/pregnancy-copilot-host-runtime-acceptance
```

```bash
PYTHONPATH=src .venv/bin/python scripts/run_synthetic_case_acceptance.py \
  --data-root /tmp/pregnancy-copilot-synthetic-cases
```

```bash
PYTHONPATH=src .venv/bin/python scripts/release_check.py \
  --root /path/to/clean-release-package
```

## Known Limits

- It is not a medical device and does not replace obstetric care.
- The host Agent is responsible for final answer generation in normal Hermes/OpenClaw mode.
- Standalone Python auto-replies require optional external LLM command hooks.
- Group chat support depends on the channel's event scopes and is not the default v0.1 claim.
- No full multi-user permission UI is included yet.
- No standalone mobile app UI is included yet.
- No cloud sync is enabled by default.

## Recommended Next Version

v0.1.5 or v0.2 should focus on real-host integration hardening:

- stable channel worker lifecycle;
- explicit pregnant-user consent commands for sharing;
- better report/lab extraction workflow;
- richer daily metrics review for weight, glucose, blood pressure, sleep, activity, and mood trends;
- safer source-search policy for medical answers;
- more portable installers for non-technical families.
