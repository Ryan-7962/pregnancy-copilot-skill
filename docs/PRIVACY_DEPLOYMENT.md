# Privacy Deployment Modes

Pregnancy Copilot supports two privacy postures.

## Same-Host Family Mode

This is the current family testing mode:

```text
Wife WeChat or pregnancy bot
  -> same Hermes/OpenClaw instance
  -> Pregnancy Copilot Skill
  -> one identity-bound local pregnancy-data/

Partner host Agent channel chat
  -> same Hermes/OpenClaw instance
```

This is convenient and good for family testing, but it is trust-based. The host Agent operator or administrator may be able to read gateway logs, raw messages, and local files.

Use this when the pregnant user explicitly trusts the person operating the host.

## Privacy-Isolated Mode

Use this for stronger privacy:

```text
Pregnant user
  -> separate host Agent/profile/instance
  -> separate pregnancy-data/
```

Recommended isolation boundaries:

- separate host Agent instance or profile,
- separate `pregnancy-data/`,
- separate message channel credentials,
- separate backups,
- explicit export/share flow for partner summaries.

v0.2.1 enforces one pregnancy identity per data root. For a multi-user host, a trusted host configuration supplies `pregnancy_id`; each identity receives an independent `identities/<pregnancy_id>/` root. New endpoints cannot claim an existing identity without explicit binding.

## Open-Source Warning

Do not claim that same-host mode prevents a technical administrator from reading private records. It does not.

The product can enforce pregnant-user-first sharing in generated summaries and artifacts, but host-level logs and filesystem access are outside the skill's control.

Backups are local ZIP archives but are not encrypted by default. Use operating-system disk encryption, restrictive file permissions, and separate backup locations when stronger isolation is required.
