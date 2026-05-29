# CLAUDE.md

Behavioral contract for agents working on Pregnancy Copilot Skill.

## Coding Rules

1. Think before coding. State assumptions, surface tradeoffs, and ask when ambiguity would change the implementation.
2. Simplicity first. Ship the minimum code that solves the requested behavior; no speculative features or one-off abstractions.
3. Surgical changes. Touch only files required by the task, match local style, and do not refactor unrelated code.
4. Goal-driven execution. Define success criteria, implement, and loop until verified.
5. Keep LLM work in the LLM and deterministic work in code. Do not replace host-agent reasoning with brittle keyword rules.
6. Use tight context budgets. Read the relevant files, not the whole repo, unless the task requires broad review.
7. Surface conflicts instead of averaging them. If docs, tests, or runtime behavior disagree, report the conflict.
8. Read before writing. Inspect adjacent code and tests before editing.
9. Tests must check behavior. A passing test that only checks implementation details is not sufficient.
10. Checkpoint long work. After meaningful milestones, report what changed and how it was verified.
11. Convention beats novelty. Existing repo patterns win unless they are demonstrably blocking the request.
12. Fail visibly. Never report success when a step was skipped, partially run, or bypassed.

## Project Rules

- This repository is a reusable skill, not a standalone app.
- The host agent supplies the LLM. The skill provides local memory, medical-state freshness, context packages, safety floor, and import/review workflows.
- Do not encode the user's private Gemini records as product rules. Use them only for local, privacy-safe category extraction and synthetic/anonymized tests.
- Historical imports are drafts unless explicitly promoted. New medical observations must refresh current state while preserving superseded values.
- Red/yellow/green triage is a safety floor, not the whole product. Ordinary chat should pass through to the host agent.
- Never package or publish `docs/private/`, real Gemini exports, Feishu message exports, local `pregnancy-data/`, `.env`, or private zip files.
- Before saying a release is ready, run unit tests, acceptance checks, release check, and package-level verification.
