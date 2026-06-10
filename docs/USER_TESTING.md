# User Testing Guide

This guide is for testing Pregnancy Copilot Skill v0.1 locally before publishing or installing it as a reusable skill.

## 1. Install Local Dependencies

Use Python 3.10+.

```bash
python3.11 -m venv .venv  # or any Python >= 3.10
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e .
.venv/bin/python -m pip install pytest
```

Run tests:

```bash
.venv/bin/python -m pytest -v
```

## 2. Initialize Local Pregnancy Data

Do not commit `pregnancy-data/`.

```bash
PYTHONPATH=src .venv/bin/python scripts/init_data_dir.py --target ./pregnancy-data
```

The Feishu event loop also creates missing directories/templates on startup, but explicit initialization is safer because it gives you a chance to edit `memory/profile.yaml` before real messages arrive.

Expected output:

```text
Initialized pregnancy data directory: pregnancy-data
```

Check:

```bash
find pregnancy-data -maxdepth 2 -type d | sort
```

You should see `inbox/`, `events/`, `memory/`, `daily_logs/`, `husband_summaries/`, `baby_diaries/`, `exports/`, and `backups/`.

## 2.1 Try Public Demo Data

The repository includes fictional demo data under:

```text
examples/demo-pregnancy-data/
```

Generate a demo daily log:

```bash
PYTHONPATH=src .venv/bin/python scripts/generate_daily_log.py \
  --data-root examples/demo-pregnancy-data \
  --date 2026-05-05
```

Inspect:

```text
examples/demo-pregnancy-data/daily_logs/2026-05-05.md
```

## 2.2 Pregnant-User-First Acceptance

Run this before handing the skill to a host Agent or another tester:

```bash
PYTHONPATH=src .venv/bin/python scripts/run_single_user_acceptance.py \
  --data-root /tmp/pregnancy-copilot-single-user-acceptance
```

Passing output should include `ok: true`. It proves:

- ordinary chat returns `handled=false`,
- pregnancy symptom messages return a host `context_package`,
- `current_medical_state.yaml` prefers the latest observation,
- older observations are preserved as `effective_status=superseded`,
- partner sharing defaults are private while the pregnant user's own local summaries remain readable.

## 2.3 Host Runtime Acceptance

Run this when the tester is Hermes/OpenClaw/Codex/Claude Code rather than a standalone Feishu event loop:

```bash
PYTHONPATH=src .venv/bin/python scripts/run_host_runtime_acceptance.py \
  --data-root /tmp/pregnancy-copilot-host-runtime-acceptance
```

Passing output should include `ok: true`. It proves:

- ordinary non-pregnancy chat is returned to the host with `handled=false`,
- ordinary non-pregnancy chat returns `host_action.type=pass_through` and writes no pregnancy memory,
- pregnancy symptom messages produce a host `context_package`,
- host responses include `host_action` so the gateway knows whether to pass through or answer with context,
- daily logs are stored without forcing a red/yellow/green visible reply,
- updated medical observations refresh `current_medical_state.yaml`,
- the local inbox, events, current context, and medical state files are created.

## 2.4 Host Default-Channel Test

Current v0.1.5 testing treats the host Agent's default chat as the pregnant user's conversation entrypoint.

```bash
PYTHONPATH=src .venv/bin/python scripts/run_host_channel_acceptance.py \
  --data-root /tmp/pregnancy-copilot-host-channel
```

Expected:

- symptom message: `handled=true`, `intent=medical_triage`, `host_action.type=answer_with_context_package`,
- ordinary chat: `handled=false`, `host_action.type=pass_through`,
- raw message saved under `inbox/raw_agent_default_messages/`.

The generic JSON bridge remains available for later adapters:

```bash
PYTHONPATH=src .venv/bin/python scripts/process_channel_message.py \
  --data-root /tmp/pregnancy-copilot-channel-bridge \
  --json '{"channel":"agent_default","chat_id":"pregnancy-default-chat","sender_id":"pregnant-user","text":"今天肚子有点紧，休息后好了"}'
```

## 2.5 Privacy-Safe Synthetic Cases

Run this when you want broader behavior checks without using private records:

```bash
PYTHONPATH=src .venv/bin/python scripts/run_synthetic_case_acceptance.py \
  --data-root /tmp/pregnancy-copilot-synthetic-cases
```

The fixture is `examples/synthetic_cases/pregnancy_synthetic_cases.json`.

Expected:

- no private raw Gemini/Feishu/medical conversation text is required,
- mild symptom messages produce `green`,
- red-flag symptom messages produce `red`,
- report, medication, diet, posture, mood, and daily log paths are handled,
- ordinary non-pregnancy chat returns `pass_through`.

These cases validate runtime behavior only. They are not medical correctness tests.

## 2.6 Private Import Category Analysis

After importing a private Gemini/Kortex zip into a local test data root, generate an aggregate category report:

```bash
PYTHONPATH=src .venv/bin/python scripts/analyze_import_categories.py \
  --data-root /tmp/pregnancy-copilot-real-gemini-test
```

For machine-readable counts:

```bash
PYTHONPATH=src .venv/bin/python scripts/analyze_import_categories.py \
  --data-root /tmp/pregnancy-copilot-real-gemini-test \
  --json
```

The report contains counts by event type and risk level only. It intentionally excludes raw user text and assistant text.

To create a local sampling aid for manual review:

```bash
PYTHONPATH=src .venv/bin/python scripts/analyze_import_categories.py \
  --data-root /tmp/pregnancy-copilot-real-gemini-test \
  --sample \
  --per-bucket 3
```

This creates `exports/manual_review_sample_report.md`. It lists event IDs, risk levels, event types, source paths, and turn indexes only. Open the raw source locally when you need to inspect the underlying private conversation.

To split manual-review items into handling lanes:

```bash
PYTHONPATH=src .venv/bin/python scripts/analyze_import_categories.py \
  --data-root /tmp/pregnancy-copilot-real-gemini-test \
  --lanes \
  --per-bucket 5
```

This creates `exports/manual_review_lane_report.md`. Use it to decide which items deserve structured medical observation extraction, medication review, urgent/yellow risk review, or historical-pattern-only handling.

To extract structured medical observation candidates without promoting them:

```bash
PYTHONPATH=src .venv/bin/python scripts/extract_medical_observation_candidates.py \
  --data-root /tmp/pregnancy-copilot-real-gemini-test
```

Outputs:

- `exports/medical_observation_candidates.jsonl`
- `exports/medical_observation_candidate_review.md`

The candidate review file excludes raw private text. Promote only after checking the private source and editing `review_decision` to `promote`.

## 2.7 Host Channel Blackbox Reply Test

Use this only when a host Agent channel is installed and connected.

The reusable runner can send cases from `examples/host_channel_blackbox_cases.json`, fetch recent chat messages, and evaluate replies:

```bash
.venv/bin/python scripts/run_host_channel_blackbox_test.py \
  --chat-id <test-chat-id> \
  --send \
  --fetch \
  --evaluate \
  --messages-output /tmp/pregnancy-copilot-host-channel-blackbox-messages.json
```

Wait about 75 seconds between messages to avoid Hermes interruptions and merged replies. The runner uses that cadence by default.

To run only selected cases:

```bash
.venv/bin/python scripts/run_host_channel_blackbox_test.py \
  --chat-id <test-chat-id> \
  --case-id PCSKILL-R05-OGTT-DIET \
  --case-id PCSKILL-R08-GENERAL \
  --send \
  --fetch \
  --evaluate
```

Manual export still works:


```bash
lark-cli im +chat-messages-list \
  --as user \
  --chat-id <test-chat-id> \
  --page-size 50 \
  --sort desc \
  --format json > /tmp/pregnancy-copilot-host-sequential-messages.json
```

Evaluate:

```bash
PYTHONPATH=src .venv/bin/python scripts/evaluate_host_channel_blackbox.py \
  --messages /tmp/pregnancy-copilot-host-sequential-messages.json
```

This checks reply-shape expectations such as green/red escalation, medication spacing, diet planning, posture dizziness, mood logging, ordinary chat pass-through behavior, and no claim that new report data was recorded unless a write tool succeeded. For ordinary chat, no skill reply is acceptable; the host Agent should answer after receiving pass-through.

## 3. Edit Profile

Open:

```text
pregnancy-data/memory/profile.yaml
```

Set at least:

- `current_gestational_age`
- `baby_nickname`
- `current_focus`
- privacy defaults

Then run:

```bash
PYTHONPATH=src .venv/bin/python scripts/check_profile_readiness.py \
  --data-root ./pregnancy-data
```

Expected for real use:

- `status=ready`
- `missing_or_template_fields=[]`

If it reports `needs_review`, edit `memory/profile.yaml` before connecting any real pregnancy chat channel.

## 4. Test Feishu Event Loop

Requirements:

- `lark-cli >= 1.0.23` installed
- app configured
- bot has permission to receive and reply to messages
- user or bot authorization completed as needed

Run readiness check first:

```bash
PYTHONPATH=src .venv/bin/python scripts/check_feishu_readiness.py
```

If you use multiple Feishu apps/profiles, specify the pregnancy bot profile:

```bash
PYTHONPATH=src .venv/bin/python scripts/check_feishu_readiness.py --profile <lark-profile>
```

Expected for v0.1:

- `ok: true` means the P2P bot path is ready.
- `p2p_event_receive.ok: true`
- `user_send_message.ok: true` if you want CLI-driven real tests.
- `group_event_receive.ok: false` is acceptable in v0.1 unless you have separately enabled and verified group message events.

Default LLM mode:

- For OpenClaw/Codex/Claude Code style usage, no separate LLM is required.
- The host Agent should use its own model with the generated context and safety rules.
- The Python event loop only needs extra LLM configuration if it must auto-reply unattended without the host Agent.

Run:

```bash
PYTHONPATH=src .venv/bin/python scripts/run_feishu_event_loop.py --data-root ./pregnancy-data
```

With a named profile:

```bash
PYTHONPATH=src .venv/bin/python scripts/run_feishu_event_loop.py \
  --data-root ./pregnancy-data \
  --profile <lark-profile>
```

Keep this process running while testing from Feishu. If it is not running, the bot can receive messages in Feishu but Pregnancy Copilot will not process or reply to them.

Optional semantic triage hook for standalone unattended mode:

```bash
export PREGNANCY_COPILOT_TRIAGE_LLM_COMMAND='your-llm-command --json'
```

The command receives the triage prompt on stdin and must print JSON on stdout:

```json
{
  "risk_level": "yellow",
  "reason": "语义上需要补充孕周和持续时间。",
  "red_flags_detected": [],
  "missing_questions": ["现在孕周是多少？"],
  "recommended_action": "记录细节，必要时联系医生。",
  "doctor_question_candidates": ["是否需要提前就诊？"]
}
```

If the command fails or prints invalid JSON, the local rule layer is used.

Optional full response hook for standalone unattended mode:

```bash
export PREGNANCY_COPILOT_RESPONSE_LLM_COMMAND='your-llm-command --text'
```

The command receives the full Pregnancy Q&A prompt on stdin and prints the final reply on stdout. If it fails or returns empty output, the deterministic triage reply is used.

Then send a message to the Feishu bot, for example:

```text
今天肚子有点紧，休息后好了，没有流血也没有流水
```

Expected local files:

- `pregnancy-data/inbox/raw_feishu_messages/YYYY-MM-DD.md`
- `pregnancy-data/events/events.jsonl`
- `pregnancy-data/memory/current_context.md`
- `pregnancy-data/daily_logs/YYYY-MM-DD.md`
- `pregnancy-data/doctor_questions/questions.jsonl` when the message creates doctor question candidates

Expected bot behavior:

- green/yellow/red risk label
- short reason
- doctor or observation guidance depending on risk level

For a CLI-driven P2P real smoke test:

```bash
PYTHONPATH=src .venv/bin/python scripts/run_feishu_p2p_smoke_test.py \
  --data-root /tmp/pregnancy-copilot-feishu-p2p-smoke \
  --bot-open-id <bot_open_id>
```

This starts the event loop, sends one no-privacy test message, checks local files, and verifies the bot reply.

Passing this smoke test proves the temporary event loop works. It does not prove that a long-running Hermes/OpenClaw worker is already attached.

To explicitly add a next-checkup question:

```text
#产检问题 下次产检要不要问宫颈长度？
```

Expected files:

- `pregnancy-data/doctor_questions/questions.jsonl`
- `pregnancy-data/doctor_questions/questions.md`
- `pregnancy-data/memory/current_context.md` contains the active question

List and update question status:

```bash
PYTHONPATH=src .venv/bin/python scripts/manage_doctor_questions.py \
  --data-root ./pregnancy-data list

PYTHONPATH=src .venv/bin/python scripts/manage_doctor_questions.py \
  --data-root ./pregnancy-data update <question_id> answered \
  --answer-summary "医生说按原计划复查。"
```

## 5. Rebuild Daily Log Manually

```bash
PYTHONPATH=src .venv/bin/python scripts/generate_daily_log.py \
  --data-root ./pregnancy-data \
  --date 2026-05-05
```

Private events are represented as placeholders and do not reveal private message summaries.

## 5.1 Rebuild Derived Memory

After imports or migrations:

```bash
PYTHONPATH=src .venv/bin/python scripts/rebuild_memory.py \
  --data-root ./pregnancy-data \
  --date 2026-05-05
```

This rebuilds current context, medical timeline, emotional pattern, and the selected daily log.

## 5.2 Generate Weekly Review and Baby Diary

From Feishu/message mode, send:

```text
#宝宝日记
```

The event processor uses the message date to generate that Monday-Sunday week.

Or run manually:

```bash
PYTHONPATH=src .venv/bin/python scripts/generate_weekly_review.py \
  --data-root ./pregnancy-data \
  --start-date 2026-05-04 \
  --end-date 2026-05-10
```

Expected files:

- `pregnancy-data/weekly_reviews/2026-05-04_to_2026-05-10.md`
- `pregnancy-data/baby_diaries/week-2026-05-04_to_2026-05-10.md`

Private events are represented as placeholders. Baby diary output is creative writing only and must not imply medical normality or fetal health.

## 5.3 Generate Visit SOPs

Generate a pre-visit doctor discussion SOP:

```bash
PYTHONPATH=src .venv/bin/python scripts/generate_pre_visit_sop.py \
  --data-root ./pregnancy-data \
  --date 2026-05-22 \
  --lookback-days 14
```

Expected file:

```text
pregnancy-data/reports/visit_sops/pre_visit_2026-05-22.md
```

It should include:

- current values from `memory/current_medical_state.yaml`,
- recent non-private daily metrics,
- recent report/risk events,
- active doctor questions.

Generate a post-visit action SOP from doctor notes:

```bash
PYTHONPATH=src .venv/bin/python scripts/generate_post_visit_sop.py \
  --data-root ./pregnancy-data \
  --date 2026-05-22 \
  --text "医生说继续观察，下次两周后复查 B 超。每天记录腹痛和出血情况。"
```

Expected files:

```text
pregnancy-data/reports/doctor_visit_notes/2026-05-22.md
pregnancy-data/reports/visit_sops/post_visit_2026-05-22.md
```

The post-visit SOP is a local summary of doctor notes. It does not automatically create or overwrite medical observations; confirmed report values should still be recorded through `scripts/record_medical_observation.py`.

## 6. Import Historical Gemini/Kortex Export

Keep real exports outside git. Zip files are ignored by `.gitignore`.

```bash
PYTHONPATH=src .venv/bin/python scripts/run_gemini_import_pipeline.py \
  "<private-history-export>.zip" \
  --data-root ./pregnancy-data
```

Outputs:

- `events/draft_import_events.jsonl`
- `events/events.jsonl`
- `exports/gemini_import_report.md`
- `exports/draft_review_report.md`
- `exports/manual_review_queue.md`
- `exports/gemini_import_pipeline_report.md`
- `memory/current_context.md`

Safety rule:

- Only green, non-report, non-medication events are promoted automatically.
- Report, medication, yellow, and red events stay in `manual_review_queue.md`.
- Imported AI summaries are memory hints, not authoritative medical facts.

## 7. Apply Manual Review Decisions

Edit:

```text
pregnancy-data/exports/manual_review_queue.md
```

For each item, check exactly one:

```markdown
- [x] promote
- [ ] skip
- [ ] correction needed
```

Apply decisions:

```bash
PYTHONPATH=src .venv/bin/python scripts/apply_manual_review_decisions.py --data-root ./pregnancy-data
```

Review:

```text
pregnancy-data/exports/manual_review_decisions_report.md
```

## 7.1 Import NotebookLM or Obsidian Markdown Notes

NotebookLM markdown directory:

```bash
PYTHONPATH=src .venv/bin/python scripts/import_notebooklm_notes.py \
  /path/to/notebooklm-markdown-dir \
  --data-root ./pregnancy-data
```

Obsidian pregnancy note directory:

```bash
PYTHONPATH=src .venv/bin/python scripts/import_obsidian_notes.py \
  /path/to/obsidian-pregnancy-notes \
  --data-root ./pregnancy-data \
  --copy-to-reports
```

These imports always create draft events and require manual review before promotion.

## 8. Backup Before Upgrade

Before running migrations or changing schema:

```bash
PYTHONPATH=src .venv/bin/python scripts/create_upgrade_backup.py \
  --data-root ./pregnancy-data \
  --target-version v0.2
```

Backups are written under:

```text
pregnancy-data/backups/
```

## 9. Privacy Checklist Before Publishing

Before pushing to GitHub:

```bash
find . -path './.venv' -prune -o -name 'pregnancy-data' -print
find . -path './.venv' -prune -o -name '*.zip' -print
find . -path './.venv' -prune -o -path './docs/private/*' -print
```

Do not publish:

- real pregnancy data
- raw Feishu exports
- Gemini/Kortex zip files
- `docs/private/`
- `.env`
