# Pregnancy Copilot Skill v0.2.1

v0.2.1 is a Public Alpha reliability release. It does not turn the project into an app or a keyword medical expert system. The host Agent's LLM remains responsible for semantic understanding and the final answer; the skill makes local pregnancy memory, time, provenance, isolation, and writes more trustworthy.

## Highlights

- All valid messages in the configured pregnant-user entrypoint receive minimum pregnancy context, so diet/travel/colloquial questions do not disappear through a keyword gap.
- Ordinary chat is not triaged and does not become a medical event.
- Progressive onboarding supports LMP/EDD and derives gestational age dynamically.
- New-install templates no longer contain realistic medical examples.
- Initialization templates ship inside the Python package, so Wheel installs no longer depend on a source-checkout-relative directory.
- Undated and low-confidence medical records remain candidates; they cannot replace a dated current fact.
- Old values remain available for trends and audit.
- Daily metrics now retain dated blood-pressure readings and recent changes alongside weight and mood context.
- Original message IDs, locks, atomic writes, and safe paths protect local memory from duplicate delivery, concurrency, and traversal.
- Multi-user hosts use explicit pregnancy identities and separate data roots.
- Backups can be verified and restored; the v0.2.1 upgrade command backs up before rebuilding state.

## Upgrade

```bash
PYTHONPATH=src .venv/bin/python scripts/upgrade_to_v021.py \
  --data-root ./pregnancy-data
```

The backup ZIP is not encrypted by default. Existing append-only inbox, events, and observations are not deleted.

## Safety

This is not a medical device and does not replace obstetric care, diagnosis, prescriptions, or emergency services. The deterministic layer is a limited red-flag fallback. Public testing and clinical-domain review are still required.

## Community

Issues, pull requests, host-Agent integration reports, and anonymized adversarial test cases are welcome. Do not attach real pregnancy records, private chat exports, credentials, or identifying health data to public issues.
