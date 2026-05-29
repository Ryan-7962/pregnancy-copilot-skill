# Privacy and Role Model

Pregnancy Copilot must treat the pregnant user as the primary user and data owner.

## Core Principle

The pregnant user owns the pregnancy data. A partner, husband, family member, or main Agent operator may help deploy the system, but is not the default administrator of private records.

Default sharing is zero sharing.

## Recommended v0.1.5 Deployment

v0.1.5 supports host-Agent runtime and Feishu P2P event-loop compatibility. The default public shape is pregnant-user-first:

```text
Pregnant user -> chat channel or pregnancy bot profile/app -> host Agent or event loop -> pregnancy-data/
```

For testing, this can be done with one Feishu app/profile:

- `pregnancy-bot`: the pregnancy bot used by the pregnant user.

The pregnancy bot must be connected to a runtime. For v0.1, that usually means the event loop runs against the pregnancy bot profile:

```bash
PYTHONPATH=src .venv/bin/python scripts/run_feishu_event_loop.py \
  --profile <lark-profile> \
  --data-root ./pregnancy-data
```

If a partner-managed host Agent reads `pregnancy-data/`, it should do so only according to the configured sharing level.

If the bot exists in Feishu but no event loop or host-Agent routing is active, it will not reply.

## Optional Partner Collaboration

Partner summaries, dad diaries, couple groups, and shared artifacts are optional extensions. They are not required for the v0.1 user journey.

When a pregnant-user channel and any partner-facing channel run inside the same Hermes/OpenClaw instance, the deployment is trust-based. The host operator may be able to read gateway logs and local files.

This is acceptable for trusted family testing, but it is not strict privacy isolation. See `docs/PRIVACY_DEPLOYMENT.md`.

## Sharing Levels

- `private`: record locally, do not expose to partner summaries.
- `summary`: share a filtered summary or care suggestion.
- `full`: share full details only after explicit confirmation.

The system should never infer consent from the fact that a technical partner installed the skill.

## Partner Features Without Wife Data

If partner collaboration is enabled, the partner can still use the skill without private pregnancy data access:

- write `#爸爸日记`
- maintain a personal question list for the next checkup
- generate family memory artifacts from shared material
- ask general pregnancy knowledge questions

## v0.2 Direction

Future versions should add an explicit invitation flow:

```text
Pregnant user enters #邀请协作者
-> bot creates an invitation/binding token
-> partner binds their identity
-> pregnant user chooses sharing level
-> partner receives only permitted summaries/artifacts
```

The collaborator setup should become a first-class optional deployment mode, but v0.1 keeps the local data core and Feishu P2P event loop small and testable.
