# Conversation Summary Public

This is a redacted summary of the project discussion for public sharing.

## Project

Pregnancy Copilot Skill: a message-first, memory-first, local-first Agent Skill for pregnancy Q&A, safety triage, prenatal visit preparation, partner co-care, and family memory artifacts.

## Key Decisions

- Use Q&A as the primary user entry point.
- Use local Markdown + JSONL memory.
- Use Feishu as MVP message channel.
- Use one bot with multiple modes.
- Keep raw data in inbox but read summaries/events by default.
- Add red/yellow/green triage and red-flag symptom rules.
- Respect privacy; partner summary is opt-in/configurable.
- Add dad diary and baby POV weekly diary, but avoid medical implications.
- Make memory migration a first-class requirement.
