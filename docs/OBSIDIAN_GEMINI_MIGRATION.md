# Obsidian Gemini State Migration

v0.1.6 adds a conservative import path for users who have already moved Gemini or NotebookLM history into Obsidian.

## Principle

Raw chat exports are high-value archives, but they are not current medical facts.

The skill imports only the refined state layer by default:

```text
Gemini/
  状态提炼/
    *状态卡-YYYY-MM-DD.md
    *待核对清单-YYYY-MM-DD.md
```

It does not read or copy raw chat files during this import.

## Command

```bash
PYTHONPATH=src python scripts/import_obsidian_gemini_state.py \
  "/path/to/Obsidian/<pregnancy-vault>/个人资料/AI对话记录/Gemini" \
  --data-root ./pregnancy-data
```

Outputs:

```text
memory/source_confidence.yaml
memory/open_review_items.yaml
memory/gemini_state_summary.md
memory/current_context.md
```

## Confidence Levels

- `report_verified`: backed by a report or health archive, but still keep the source path.
- `user_reported`: symptom, habit, weight, mood, or user correction.
- `gemini_inferred`: model inference or discussion clue only.
- `needs_review`: conflict, stale value, or missing source; do not use as current medical fact.

## Host Model Rule

The host Agent should answer from:

1. `memory/current_medical_state.yaml`
2. `memory/source_confidence.yaml`
3. `memory/open_review_items.yaml`
4. recent events and current context

If a migrated Gemini note conflicts with a newer report, the newer report wins. If the source is unclear, ask for the report date, original text, value, unit, or doctor conclusion.
