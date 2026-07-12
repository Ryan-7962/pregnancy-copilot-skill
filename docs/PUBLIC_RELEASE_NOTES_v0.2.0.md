# Pregnancy Copilot Skill v0.2.0

v0.2.0 makes truthful first-run onboarding a required part of the host-Agent contract.

## What Changed

- The host Agent can proactively request pregnancy profile setup immediately after installation.
- If proactive messaging is unavailable, the first incoming message triggers the same onboarding flow, including ordinary chat.
- The onboarding message explains the real privacy boundary: structured memory stays in the user-selected local `pregnancy-data/`, while the selected chat channel and host model may still process messages.
- Users are asked to copy report values, units, dates, and doctor conclusions from original sources and leave unavailable information explicitly unknown.
- Automatically extracted NT, CRL, fetal-heart-rate, and placenta observations now use `status: unknown`; the Skill no longer silently labels them normal.
- General chat returns to the host Agent after profile readiness.

## Upgrade Notes

Back up an existing data directory before upgrading:

```bash
PYTHONPATH=src python scripts/create_upgrade_backup.py \
  --data-root ./pregnancy-data \
  --target-version v0.2.0
```

The data schema remains `0.1`; no destructive migration is required. Existing observations and historical values remain append-only.

## Validation

- Full automated test suite
- Host Runtime acceptance flow
- Fresh-profile first-message onboarding
- Post-onboarding general-chat pass-through
- Release-package privacy scan
