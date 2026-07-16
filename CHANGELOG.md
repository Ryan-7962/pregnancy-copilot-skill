# Changelog

## v0.4.0 - 2026-07-16

### External Content Audit

- Add optional Xiaohongshu URL detection, allowlisted redirect handling, and structured SSR extraction without JavaScript evaluation.
- Add terminal-only Cookie setup with mode `0600`; credentials stay outside `pregnancy-data/` and never enter chat or release artifacts.
- Add bounded image download and host vision/OCR handoff; source text and embedded instructions remain untrusted quoted material.
- Add consent-aware video transcription policies and optional SiliconFlow ASR using explicit supported model IDs.
- Add local source Markdown, append-only JSONL history, deterministic compact index, deduplication, and relevant-only memory retrieval.
- Keep all external claims `social_media_unverified`; they cannot update profile, medical observations, medications, doctor orders, or current medical state.
- Add per-message no-record handling and default post-analysis media cleanup.

### Upgrade And Verification

- Add backup-first v0.3.0 -> v0.4.0 migration without rewriting append-only event or medical-observation history.
- Add synthetic parser, credential, network, media, ASR, prompt-injection, privacy, lifecycle, and Host Runtime tests.

## v0.3.0 - 2026-07-15

### First-Use Experience

- Replace the blocking profile gate with answer-first adaptive onboarding.
- Add persistent tutorial topics, skip/resume controls, and per-message no-record behavior.
- Keep onboarding UX state separate from profile and medical facts.

### Daily Memory And Prenatal Plan

- Add deterministic daily consolidation and a compact local conversation index.
- Mark optional host summaries as `ai_organized` with no medical-fact effect.
- Add source-aware prenatal plan items, schedule history, pre-visit artifacts, and idempotent reminder actions.
- Add scheduler-facing commands while keeping scheduling and channel delivery owned by the host.

### Upgrade

- Add backup-first v0.2.1 -> v0.3.0 migration without rewriting append-only history.

## v0.2.1 - 2026-07-15

### Reliability

- Route every valid message from the configured pregnant-user entrypoint through the minimum host context; ordinary chat remains non-medical.
- Fix negation/turn handling for phrases such as "previously no bleeding, now bleeding" and broaden the explicit fetal-movement fallback.
- Remove realistic pregnancy, hospital, and medical-focus facts from new-install templates.
- Package initialization templates inside the Python distribution so Wheel installs work outside the source checkout.
- Prefer original channel message/event IDs and make raw/event/observation writes idempotent and concurrency-safe.
- Validate filesystem path components and block traversal outside the local data root.

### Onboarding And Memory

- Add progressive extraction for LMP, EDD, demographics, weights, hospital, history, medications, allergies, doctor orders, focus, and next checkup.
- Derive gestational age dynamically from LMP/EDD.
- Keep undated and low-confidence observations as candidates instead of current facts.
- Preserve provenance, current values, historical values, candidates, and daily trends separately.
- Track dated blood-pressure readings and recent deltas alongside weight and mood history.
- Add explicit single- and multi-pregnancy identity binding.

### Upgrade And Privacy

- Add non-overwriting backups, archive validation, safe restore, and v0.2.0 -> v0.2.1 migration.
- Expand release privacy scanning for local absolute paths, token shapes, bot IDs, private archives, and generated files.
- Clarify that local ZIP backups are not encrypted by default.

### Verification

- Add adversarial tests for semantic routing, emergency-before-profile, LMP-only onboarding, temporal medical selection, identity isolation, path traversal, concurrency, idempotency, LLM failure/refusal, provenance, and backup restore.

## v0.2.0 - 2026-07-12

- Added required first-run onboarding and public release packaging.
- Kept auto-extracted report interpretation unknown until reviewed.
- Published the first external-testing release.
