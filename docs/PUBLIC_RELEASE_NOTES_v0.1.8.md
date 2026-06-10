# Pregnancy Copilot Skill v0.1.8 Release Notes

Date: 2026-06-10

v0.1.8 adds a lightweight prenatal-visit workflow on top of the existing local memory system.

## What Changed

- Added pre-visit SOP generation:
  - reads active doctor questions,
  - reads current medical state,
  - includes recent non-private risk/report events,
  - includes recent daily metrics such as weight, mood, sleep, diet, and activity.
- Added post-visit action SOP generation:
  - saves the doctor's original note locally,
  - appends a `doctor_visit_summary` event,
  - creates action, follow-up, and uncertainty sections.
- Added CLI scripts:
  - `scripts/generate_pre_visit_sop.py`
  - `scripts/generate_post_visit_sop.py`
- Added test coverage for private filtering, current-vs-history medical state usage, doctor question inclusion, and doctor note persistence.

## What This Does Not Do Yet

- It does not replace a doctor or make a diagnosis.
- It does not automatically parse OCR reports into medical observations.
- It does not automatically create calendar reminders.
- It does not overwrite current medical state from a doctor note; confirmed values still need structured observation writes.

## Test

```bash
.venv/bin/python -m pytest -q
PYTHONPATH=src .venv/bin/python scripts/build_release_package.py --source . --target /tmp/pregnancy-copilot-skill-v0.1.8-release
PYTHONPATH=src .venv/bin/python scripts/release_check.py --root /tmp/pregnancy-copilot-skill-v0.1.8-release
```
