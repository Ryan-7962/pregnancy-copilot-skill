# Historical v0.1 Status and Gaps

Date: 2026-06-10

> Historical snapshot only. For current v0.2.1 behavior and release claims, use `README.md`, `CHANGELOG.md`, and `docs/PUBLIC_RELEASE_NOTES_v0.2.1.md`.

## Current Completion Estimate

Engineering completion for the planned v0.1 skeleton is about 97%.

Product completion compared with the full original Pregnancy Copilot vision is about 35-45%.

The current version is a usable local-first skill skeleton, not yet a full pregnancy copilot product.

## What v0.1 Can Do Now

- Initialize local `pregnancy-data/`.
- Create `profile.yaml` and memory templates.
- Save raw Feishu-like messages to `inbox/`.
- Append structured events to `events/events.jsonl`.
- Enforce `schema_version`.
- Generate `memory/current_context.md`.
- Generate daily logs.
- Generate optional partner summary text from daily logs.
- Generate optional dad diary markdown from `#爸爸日记`.
- Generate baby weekly diary markdown.
- Run red/yellow/green safety triage with a local rule layer and optional semantic LLM advisor.
- Configure external standalone commands with `PREGNANCY_COPILOT_TRIAGE_LLM_COMMAND` and `PREGNANCY_COPILOT_RESPONSE_LLM_COMMAND`.
- Detect key red flags such as bleeding, decreased fetal movement, severe headache with vision change.
- Route message commands such as `#爸爸日记`, `#只同步建议`, `#不同步`, `#产检问题`.
- Use Feishu CLI adapter for receive/reply/doc-create interfaces.
- Run Feishu event loop with `lark-cli`.
- Auto-initialize missing `pregnancy-data/` directories/templates when the event loop starts.
- Select Feishu app/profile with `--profile`, useful for testing different pregnancy chat bots or channels.
- Import Gemini/Kortex markdown zip to draft events.
- Import NotebookLM markdown notes to draft events.
- Import Obsidian markdown notes to draft events and optional reports.
- Promote only safe low-risk imported drafts automatically.
- Generate manual review queues for medical/high-risk imports.
- Apply manual review decisions.
- Create upgrade backup zip.
- Build a clean GitHub release package excluding private files.
- Run local install check without real Feishu.
- Process host-Agent child conversation messages through `pregnancy_copilot.host_runtime.process_host_message`.
- Return `reply_text`, `risk_level`, `event_id`, mode, privacy level, artifacts, and event payload to Hermes/OpenClaw without requiring a separate Feishu event loop.
- Classify incoming messages with intent routing.
- Return `handled=false` for ordinary host-Agent chat so Hermes/OpenClaw can answer normally.
- Show red/yellow/green only when `triage_required=true`; pregnancy logs, mood support, and diary entries use `risk_level=not_applicable` and no longer get a visible green-light reply.
- Record structured medical observations and regenerate `memory/current_medical_state.yaml` so newer B 超/化验/医嘱 values supersede older stale values while preserving the full history.
- Generate a pre-visit doctor discussion SOP from current medical state, recent daily metrics, recent non-private risk/report events, and active doctor questions.
- Save post-visit doctor notes and generate a post-visit action SOP with action/follow-up/uncertain-item sections.

## What Is Still Not Done for v0.1 Product Polish

These are not blockers for a technical v0.1 skeleton, but they matter before calling it a polished public product.

1. Full answer generation depends on host Agent mode or optional standalone commands.
   - `PromptBuilder` exists.
   - Host Agent mode should use the installing Agent's model directly.
   - Standalone event loop can call optional command providers.
   - No specific model vendor is bundled.

2. Feishu integration is real enough for message reply tests, but not complete as a public installer.
   - Users must configure `lark-cli` themselves.
   - `lark-cli >= 1.0.23` is required.
   - Commands can pass `--profile <name>` when multiple Feishu apps are configured.
   - `scripts/check_feishu_readiness.py` reports doctor/auth/event readiness and common missing scopes.
   - P2P bot chat is the verified v0.1 real path only while a Pregnancy Copilot event loop is running for that bot profile.
   - Smoke tests start a temporary event loop; they do not prove a persistent Hermes/OpenClaw connection exists.
   - Group chat events are not yet claimed as supported until group message event scopes/config are verified.
   - There is no guided auth setup wizard.

3. Doctor question and visit SOP lifecycle is basic but usable.
   - Questions are extracted into `doctor_questions/questions.jsonl`.
   - Explicit `#产检问题` messages are added to the same list.
   - Status tracking supports `open / asked / answered / archived`.
   - `scripts/generate_pre_visit_sop.py` creates a Markdown package for the next doctor visit.
   - `scripts/generate_post_visit_sop.py` saves doctor notes and creates a next-stage action SOP.
   - There is not yet a polished Feishu UI for updating statuses.
   - There is not yet calendar/reminder integration for the generated follow-ups.

4. Partner summary is generated locally but not part of the default v0.1 path.
   - Summary template exists.
   - Private filtering exists.
   - Consent-aware full sharing workflow is not fully implemented.
   - Automatic Feishu doc or group sync for partner summary is not complete.
   - Pregnant-user-first consent is documented, but full invitation/binding flow is not implemented.

5. Baby weekly diary is generated from a weekly review.
   - Safe generation exists and filters medical promises.
   - `scripts/generate_weekly_review.py` gathers a date range into `weekly_reviews/`.
   - `#宝宝日记` generates the current message week.
   - It writes `baby_diaries/week-*.md` from weekly review, dad diary summaries, and prenatal/report signals.
   - There is no weekly scheduler.

6. Medical timeline and current state are basic but not yet fully automated.
   - `memory/current_medical_state.yaml` can be rebuilt from structured observations.
   - `memory/medical_observation_timeline.md` preserves historical measurements.
   - There is not yet a robust OCR/report parser; observations still need manual or LLM-assisted extraction.

7. Emotional pattern memory is not automatically rebuilt.
   - `memory/emotional_pattern.md` template exists.
   - Events can include emotion-like content.
   - No dedicated emotional summarizer exists yet.

8. Report explanation is not a full workflow.
   - Report questions become yellow risk.
   - Imported report notes require manual review.
   - No structured report parser or report-specific answer generator exists.

9. Weight, blood glucose, blood pressure, medication reminders are not implemented.
   - These remain roadmap/schema-level ideas.
   - No reminder scheduler or time-series management exists.

10. No vector search or semantic retrieval.
    - v0.1 relies on current context, recent events, and manual imports.
    - This is safer and simpler, but less powerful for long histories.

11. No hosted multi-user product.
    - No user accounts.
    - No web app.
    - No cloud database.
    - No encrypted sync.

12. No mobile-native UX.
    - Feishu is the first channel.
    - There is no standalone app, WeChat integration, or Telegram integration.

## Difference From the Full Original Vision

The full vision was:

- a message-first pregnancy copilot
- with long-term pregnancy memory
- usable by pregnant user first, with optional partner extensions
- connected to Feishu first, later more channels
- able to import historical AI conversations
- able to explain reports carefully
- able to produce daily/weekly family artifacts
- safe enough for pregnancy risk triage
- publishable as a reusable skill

Current v0.1 delivers the foundation:

- local memory substrate
- event log
- safety triage
- Feishu adapter shape
- history import drafts
- basic artifacts
- doctor question status tracking and basic visit SOP artifacts
- privacy-first release packaging

It does not yet deliver the full product experience:

- no high-quality LLM answer runtime
- no polished multi-step consent flow
- no full report understanding
- no reminder/calendar system
- no automatic long-term memory compression
- no multi-channel support
- no non-technical onboarding
- no packaged Hermes/OpenClaw background-worker installer

## Recommended Next Milestones

### v0.1.2 Host Agent Integration

- Make Hermes/OpenClaw parent-Agent mode the preferred runtime.
- Treat the pregnant-user pregnancy bot/window as a host-Agent conversation entrypoint, not a separate product.
- Keep standalone Feishu event loop as a compatibility and smoke-test path.

### v0.1.3 Intent Router and Conditional Triage

- Add channel-agnostic intent classification inside the skill.
- Keep WeChat/Feishu adapters free of pregnancy keyword business logic.
- Document same-host family privacy and privacy-isolated deployment options.

### v0.1.1 Public Hardening

- Add install guide screenshots or step-by-step Feishu CLI setup.
- Add better permission error messages.
- Add command examples for `#产检问题`, `#宝宝日记`, `#备份`.
- Add public demo walkthrough.
- Add clearer one-profile examples for a pregnant-user bot plus optional partner extension notes.

### v0.2 Memory Upgrade

- Generate `medical_timeline.md` from reviewed report events.
- Generate `emotional_pattern.md` from daily logs.
- Add safer report explanation prompt pipeline.

### v0.3 Product Workflows

- China pregnancy checkup calendar template.
- Feishu docs/sheets sync.
- Weight/blood pressure/blood glucose/medication events.
- Reminder workflows.

### v1.0 Public Skill

- Real LLM provider integration.
- Better onboarding.
- Expanded safety tests.
- Multi-channel adapter examples.
- Privacy/security documentation.
- Migration tooling.

## Can Other Users Install It Now?

Yes, other technical users can install and run the local v0.1 skeleton if they can:

- use Python 3.10+
- run local scripts
- configure their own `lark-cli` if they want Feishu
- accept local file-based storage

They should run:

```bash
PYTHONPATH=src python scripts/install_check.py --data-root /tmp/pregnancy-copilot-install-check
```

If this passes, the local memory core works.

For Feishu usage, they still need to configure their own Feishu app, bot, scopes, and event subscription.
