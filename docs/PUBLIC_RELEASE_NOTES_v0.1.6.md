# Public Release Notes v0.1.6

Pregnancy Copilot Skill v0.1.6 focuses on portable personalization and safer Gemini/NotebookLM memory migration.

## What Changed

- Added optional response style configuration in `memory/profile.yaml`.
- Kept the default style neutral and medically cautious; personal "geek" style requires explicit opt-in.
- Added optional `memory/agent_soul.md` support for user-approved host Agent persona notes.
- Added Obsidian Gemini refined-state import:
  - reads `状态提炼/*状态卡-*.md`;
  - reads `状态提炼/*待核对清单-*.md`;
  - does not read raw Gemini chat files by default.
- Added `memory/source_confidence.yaml` with `report_verified`, `user_reported`, `gemini_inferred`, and `needs_review`.
- Added `memory/open_review_items.yaml` for stale, conflicting, or report-needed items.
- Added source-confidence and open-review sections to `memory/current_context.md`.
- Strengthened host instructions: migrated Gemini/NotebookLM history is a clue layer, not a medical fact layer.

## Why It Matters

Gemini and NotebookLM can work well when a user keeps a rich knowledge base, but account migration and long histories create two risks:

- old values may be mistaken for current values;
- one user's personal prompt style may be copied into another user's assistant.

v0.1.6 keeps the durable parts: source confidence, open questions, current medical state priority, and explicit user-controlled style.

## Verified Checks

```bash
.venv/bin/python -m pytest -q
```

```bash
PYTHONPATH=src .venv/bin/python scripts/import_obsidian_gemini_state.py \
  "/path/to/Gemini" \
  --data-root /tmp/pregnancy-copilot-obsidian-import
```

```bash
PYTHONPATH=src .venv/bin/python scripts/release_check.py \
  --root /path/to/clean-release-package
```
