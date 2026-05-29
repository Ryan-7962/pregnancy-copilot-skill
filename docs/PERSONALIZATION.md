# Personalization and Agent Soul

Pregnancy Copilot should not hard-code one family's tone, nicknames, metaphors, hospital, or relationship model.

The default style is `neutral_clinical`: clear, structured, medically cautious, and concise.

## Why

Some users like a technical or playful style. Others need plain language. A migrated Gemini or NotebookLM prompt can be valuable, but it is a personal preference layer, not the product default.

## Profile Config

Set this in `memory/profile.yaml` only after the pregnant user or installer explicitly chooses it:

```yaml
preferences:
  response_style:
    enabled: true
    preset: "geek_ops"
    nickname: "孕妇用户"
    baby_nickname: "宝宝"
    custom_terms:
      body: "身体系统"
      baby: "胎儿发育系统"
```

Rules:

- `enabled: false` keeps the default neutral style.
- `geek_ops` allows technical metaphors, but only as explanation aids.
- The host model must not inherit private nicknames, locations, hospitals, or family roles from another user's prompt.
- Medical facts, safety escalation, and source confidence always override style.

## Agent Soul File

If the host Agent already has a user-approved "soul" or persona note, store a short local file:

```text
pregnancy-data/memory/agent_soul.md
```

Then reference it:

```yaml
preferences:
  response_style:
    enabled: true
    preset: "neutral_clinical"
    agent_soul_path: "memory/agent_soul.md"
```

The skill passes a bounded excerpt into the host context package. This is optional and never replaces safety rules.

## Migration Prompts

Gemini or NotebookLM migration prompts should be treated as source material. Extract durable preferences from them, then write only those preferences into `profile.yaml` or `agent_soul.md`.

Do not paste another user's full boot prompt into a public skill package.
