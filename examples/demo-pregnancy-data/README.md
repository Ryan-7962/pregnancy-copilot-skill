# Demo Pregnancy Data

This directory contains fully fictional demo data for testing Pregnancy Copilot Skill.

It is safe to publish because it does not contain real pregnancy data, real Feishu IDs, real medical records, or private chat logs.

Try:

```bash
PYTHONPATH=src python scripts/generate_daily_log.py \
  --data-root examples/demo-pregnancy-data \
  --date 2026-05-05
```

Then inspect:

```text
examples/demo-pregnancy-data/daily_logs/2026-05-05.md
```
