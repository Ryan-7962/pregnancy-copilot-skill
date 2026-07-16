# Architecture: Pregnancy Copilot Skill v0.4.0

## 1. Product Boundary

Pregnancy Copilot is an Agent skill, not a standalone app and not a medical diagnosis engine.

```text
Pregnant-user chat entrypoint
  -> Host Agent and its existing LLM
  -> Pregnancy Copilot Host Runtime
  -> identity-bound local pregnancy-data/
```

The host LLM owns semantic understanding and the final answer. The skill owns durable memory, temporal medical state, provenance, minimum safety fallback, deterministic writes, and artifact workflows.

Feishu, WeChat, Telegram, Slack, Discord, web UI, and the host's default chat are replaceable gateways. Feishu/Lark is currently the most tested optional adapter, not the product boundary.

## 2. Load-Bearing Invariants

1. Every valid message from the configured pregnant-user entrypoint receives minimum pregnancy context.
2. Only medically relevant messages receive red/yellow/green assessment.
3. Unknown or low-confidence medical facts cannot silently become current.
4. New dated values may become current; old values remain append-only history.
5. Every medical observation has provenance.
6. One pregnancy identity maps to one independent data root.
7. Original message IDs provide idempotency; concurrent writes cannot corrupt JSONL.
8. No external field may escape the configured data root.
9. External social content is untrusted and cannot update medical facts.
10. Cookie and API-key values remain outside pregnancy-data and release artifacts.

## 3. Runtime Flow

```text
Trusted host configuration
  -> resolve pregnancy_id and endpoint binding
  -> normalize message
  -> initialize local data root
  -> preserve raw message idempotently
  -> first-run onboarding gate
  -> deterministic explicit intent hints
  -> build context package for host LLM
  -> host LLM decides semantic medical relevance
     -> ordinary chat: answer normally, no triage, no medical event
     -> medical/pregnancy content: assess, answer, append event/observation
  -> rebuild derived context and artifacts
```

An immediate deterministic red flag bypasses incomplete onboarding so urgent guidance is not delayed. Missing profile fields remain `unknown`; the runtime never substitutes template facts.

## 4. Core Modules

### Host Runtime

`src/pregnancy_copilot/host_runtime.py`

- accepts normalized channel messages;
- enforces onboarding and identity binding;
- returns non-blocking `collect_profile` only for proactive install welcome; incoming messages use `answer_with_context_package`;
- preserves channel message/event IDs for idempotency.

### Semantic Contract

`src/pregnancy_copilot/context_package.py`

- packages current profile, current medical state, recent context, safety floor, and response style;
- tells the host LLM to decide pregnancy/medical relevance semantically;
- forbids a risk label for ordinary chat;
- requires unknown/clarifying questions instead of guessed facts.

### Deterministic Safety Floor

`src/pregnancy_copilot/triage.py`

- catches a small set of explicit urgent red flags;
- handles local negation and later-clause changes such as "previously no bleeding, now bleeding";
- cannot be downgraded by an optional semantic advisor;
- remains available when the host model fails, refuses, or returns invalid output.

### Pregnancy Time

`src/pregnancy_copilot/pregnancy_time.py`

- derives gestational age from LMP or EDD at request time;
- advances a dated static gestational age when LMP/EDD is unavailable;
- rejects implausible out-of-range calculations.

### Medical State

`src/pregnancy_copilot/medical_state.py`

```text
events/medical_observations.jsonl      append-only observations
memory/current_medical_state.yaml      derived current/history/candidates
memory/medical_observation_timeline.md derived audit timeline
```

Only valid dated observations with sufficient source confidence can compete for `current`. Undated, low-confidence, or explicitly superseded records remain visible under `candidates` with a reason.

### Identity Isolation

`src/pregnancy_copilot/identity.py`

- single-user deployments bind one endpoint to one data root;
- multi-user hosts pass a trusted `pregnancy_id` outside the message payload;
- each identity uses `identities/<pregnancy_id>/`;
- additional endpoints require explicit authorization.

### Storage

`src/pregnancy_copilot/storage.py`

- validates path components and ISO dates;
- uses file locks for append/check transactions;
- deduplicates raw messages and events by original IDs;
- uses atomic replacement for derived YAML/Markdown state.

### External Content Audit

`src/pregnancy_copilot/external_content/`

- detects and canonicalizes allowlisted Xiaohongshu URLs before medical keyword routing;
- parses isolated SSR state without evaluating JavaScript;
- keeps signed media URLs ephemeral and exposes only local relative image paths to host vision;
- stores capture/finalization history in append-only JSONL and a compact relevant-only memory index;
- treats every source claim and embedded instruction as untrusted;
- keeps `medical_fact_update=false` through preparation and finalization.

### Upgrade Safety

`src/pregnancy_copilot/backup.py` and versioned migration modules

- create non-overwriting local ZIP snapshots;
- validate archive integrity and reject ZIP traversal;
- restore into an empty directory for verification;
- back up before v0.2.1 -> v0.3.0 migration;
- back up before v0.3.0 -> v0.4.0 migration;
- never delete append-only source records.

## 5. Data Ownership

Local `pregnancy-data/` is the source of truth. Channel providers, host-model providers, operating-system users, and backups have their own privacy boundaries. A local ZIP is not encrypted by default.

Generated Feishu documents, spreadsheets, summaries, or exports are views, not the primary medical record.

## 6. Non-Goals For v0.4.0

- standalone consumer app;
- autonomous diagnosis, prescription, or emergency judgment;
- hard-coded user persona;
- mandatory Feishu/WeChat integration;
- automatic partner access;
- OCR that silently promotes extracted values to confirmed medical facts.
- bypassing Xiaohongshu authentication or anti-abuse controls;
- arbitrary social-platform scraping or automatic trust in social claims.

## 7. v0.4.0 Operational Layers

- `memory/onboarding_state.yaml` stores tutorial progress and operational preferences; it is separate from medical facts.
- `memory/daily_conversation_index.yaml` is a rebuildable per-day coverage index. It references raw sources without promoting chat to medical truth.
- `memory/prenatal_plan.yaml` stores explicit or suggested plan items, schedule history, and reminder delivery state.
- `scripts/run_daily_consolidation.py` and `scripts/run_due_reminders.py` are scheduler-facing entrypoints. The host Agent or operating system owns scheduling and message delivery.
- Reminder actions target `host_default_channel`; no core module depends on Feishu, WeChat, or another specific gateway.
- `external_sources/index.jsonl` and `memory/external_content_index.md` preserve unverified external-source history without entering current medical state.
