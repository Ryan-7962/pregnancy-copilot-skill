# Pregnancy Copilot Skill v0.1.7 Release Notes

Date: 2026-05-29

## What Changed

- Added first-run profile onboarding gate. If the profile is still missing key pregnancy anchors or contains template values, normal pregnancy questions now ask the user to complete baseline profile/latest report data first.
- Added structured onboarding intake. A clear `建档信息` message can update `profile.yaml` and write initial report observations such as NT, CRL, fetal heart rate, and placenta position.
- Added report observation refresh after onboarding. Later report messages can update the same metric keys; the newest value becomes current and older values remain in `previous_values`.
- Preserved emergency behavior. Immediate red-flag messages can still bypass onboarding and return urgent safety guidance.
- Added `scripts/run_feishu_runtime_worker.py` for deterministic Feishu bot testing. It reads new Feishu user messages, calls the Host Runtime, and replies with the runtime `reply_text` exactly.
- Added privacy release exclusions for local Gemini/real pregnancy source folders so private test material is not copied into public packages.
- Added persisted event de-duplication so repeated worker scans do not duplicate already recorded pregnancy events.
- Added a macOS `launchd` worker template for persistent local testing, with public placeholders instead of real bot/chat/profile values.
- Moved local private source folder exclusions into `.releaseignore.local`, which is excluded from public packages.

## Why It Matters

The skill should not let a host Agent answer using stale template data, old visible chat history, or another user's imported pregnancy profile. v0.1.7 makes fresh installs safer by forcing profile setup before routine medical-memory answers.

## Upgrade Notes

Before upgrading a real `pregnancy-data/` directory:

```bash
PYTHONPATH=src python scripts/create_upgrade_backup.py \
  --data-root ./pregnancy-data \
  --target-version v0.1.7
```

For Feishu/Hermes testing, use a dedicated bot profile and either:

- Host Agent Runtime integration, where the host sends `collect_profile` `reply_text` as-is; or
- direct Feishu runtime worker, where no host-Agent paraphrase is involved.

Do not run Hermes gateway and the direct runtime worker against the same bot at the same time unless duplicate replies are acceptable during debugging.
