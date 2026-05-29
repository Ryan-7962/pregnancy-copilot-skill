# GitHub Release Guide

This repository should be published from a clean release directory, not from the local handoff folder.

The local handoff folder may contain private source material such as `docs/private/`, raw Gemini cases, local virtual environments, and historical zip packages. Those files are intentionally excluded from the release package.

Current public version target: `v0.1.7`.

## Public Positioning To Use On GitHub

Short description:

```text
Long-term pregnancy health assistant built on LLM + Agent workflows. It helps families keep pregnancy Q&A grounded in current medical facts, source history, daily logs, and family artifacts without locking users into one model or chat channel.
```

README framing:

- This is an Agent Skill, not a standalone pregnancy app.
- The host Agent supplies the LLM; the skill supplies durable pregnancy memory, current medical state, safety floor, artifacts, and adapters.
- The main pain point is not "AI cannot answer pregnancy questions"; the pain point is long-term pregnancy context, stale report data, fragmented records, and privacy-safe migration across models/channels.
- Feishu/Lark is an optional adapter. Do not present it as the only product path.
- Do not use private family examples, real report snippets, real names, real locations, bot IDs, chat IDs, or exported chat text in public docs.

## 1. Build A Clean Release Directory

From the handoff folder:

```bash
PYTHONPATH=src .venv/bin/python scripts/build_release_package.py \
  --source . \
  --target /tmp/pregnancy-copilot-skill-release
```

Verify:

```bash
PYTHONPATH=src .venv/bin/python scripts/release_check.py \
  --root /tmp/pregnancy-copilot-skill-release
```

Expected:

```text
Release check passed: no private/generated blockers found.
```

## 2. Test The Release Directory

```bash
cd /tmp/pregnancy-copilot-skill-release
python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e .
.venv/bin/python -m pip install pytest
.venv/bin/python -m pytest -q
PYTHONPATH=src .venv/bin/python scripts/run_single_user_acceptance.py --data-root /tmp/pregnancy-copilot-single-user-acceptance
PYTHONPATH=src .venv/bin/python scripts/run_host_runtime_acceptance.py --data-root /tmp/pregnancy-copilot-host-runtime-acceptance
PYTHONPATH=src .venv/bin/python scripts/run_host_channel_acceptance.py --data-root /tmp/pregnancy-copilot-host-channel
PYTHONPATH=src .venv/bin/python scripts/run_synthetic_case_acceptance.py --data-root /tmp/pregnancy-copilot-synthetic-cases
```

Testing inside the release directory creates local `.venv/`, `.pytest_cache/`, and `__pycache__/` files. Rebuild the release directory from the handoff folder before initializing Git or creating the zip:

```bash
cd /path/to/pregnancy-copilot-skill-handoff
PYTHONPATH=src .venv/bin/python scripts/build_release_package.py \
  --source . \
  --target /tmp/pregnancy-copilot-skill-release
PYTHONPATH=src .venv/bin/python scripts/release_check.py \
  --root /tmp/pregnancy-copilot-skill-release
```

## 3. Initialize Git From The Clean Directory

```bash
cd /tmp/pregnancy-copilot-skill-release
git init
git add .
git commit -m "Release Pregnancy Copilot Skill v0.1.7"
```

## 4. Publish

Create a GitHub repository, then push:

```bash
git branch -M main
git remote add origin git@github.com:<owner>/pregnancy-copilot-skill.git
git push -u origin main
```

Recommended initial repository settings:

- enable GitHub Actions,
- enable secret scanning if available,
- protect `main` after the first push,
- keep real pregnancy data out of issues and discussions,
- publish v0.1.7 as a pre-release until more external testers validate host-Agent integration.

## 5. Tag v0.1.7

```bash
git tag -a v0.1.7 -m "Pregnancy Copilot Skill v0.1.7"
git push origin v0.1.7
```

Attach the checked zip package only if it was built from the clean release directory and passes `scripts/release_check.py`.
