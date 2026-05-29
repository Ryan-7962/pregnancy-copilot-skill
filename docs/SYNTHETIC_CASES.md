# Synthetic Cases

`examples/synthetic_cases/pregnancy_synthetic_cases.json` is a public-safe test fixture.

It is inspired by broad patterns from private pregnancy-agent usage, but it is not an export or sanitization of raw conversations. Cases are manually generalized and rewritten so they contain no names, exact dates, locations, hospital identifiers, account identifiers, or raw private phrasing.

Use these cases to test runtime behavior:

- whether pregnancy-related messages are handled by the skill,
- whether ordinary chat passes through to the host Agent,
- whether medically relevant messages include a context package for the host LLM,
- whether non-triage logs avoid visible red/yellow/green framing,
- whether raw inbox, events, and `current_context.md` are written.

Do not use these cases to validate medical correctness. Medical judgment should remain with the host LLM plus current user profile, current medical state, and clinician guidance.

Run:

```bash
PYTHONPATH=src python scripts/run_synthetic_case_acceptance.py \
  --data-root /tmp/pregnancy-copilot-synthetic-cases
```
