# Pregnancy Copilot Skill v0.3.0

v0.3.0 turns first use into an answer-first pregnancy-assistant experience and adds explicit daily-memory and prenatal-reminder workflows. It remains an Agent Skill, not a standalone app or medical device.

## Highlights

- Adaptive onboarding is not limited to five turns and never blocks the current question.
- New users receive short, progressive guidance about capabilities, medical boundaries, privacy, truthful report entry, and local memory.
- `跳过教程`, `继续教程`, and `这条不记录` are supported.
- Daily consolidation creates a local daily log and compact conversation index without inventing medical facts.
- Prenatal plan items preserve source and rescheduling history.
- D-N reminder actions are channel-neutral and claimed once per item/lead date.
- The host Agent or operating system owns scheduling and message delivery.
- v0.2.1 data upgrades through a verified local backup without rewriting append-only history.

## Upgrade

```bash
PYTHONPATH=src .venv/bin/python scripts/upgrade_to_v030.py \
  --data-root ./pregnancy-data
```

## Boundaries

- No diagnosis, prescription, or emergency replacement.
- No automatic background process is installed.
- No generic guideline suggestion silently becomes a confirmed hospital appointment.
- Local-first describes the durable data source; the selected host model and chat channel retain their own privacy boundaries.
